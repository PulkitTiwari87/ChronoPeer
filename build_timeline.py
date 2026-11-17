#!/usr/bin/env python3
"""Reproducible timeline builder for DF-PBL-040.
Usage: python3 -I build_timeline.py <path-to-EVTX-ATTACK-SAMPLES> <out_dir>
Verifies SHA-256 of each evidence file, parses Sysmon events, writes timeline.csv.
Needs: pip install python-evtx lxml
"""
import sys, os, csv, hashlib
import Evtx.Evtx as evtx
from lxml import etree

NS = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}
EVIDENCE = [  # (label, relative path, expected SHA-256)
    ('A', 'Lateral Movement/LM_sysmon_psexec_smb_meterpreter.evtx',
     '18ffdda9c24e593d6b1414b6e05c7f7a5dbffb8588a387c165431b61ab52d76f'),
    ('B', 'Lateral Movement/LM_wmiexec_impacket_sysmon_whoami.evtx',
     '21b8852b2b386f4d3f6f0c8a7304de8e628bb43cfa23888ab317b95b784ffe59'),
    ('C', 'Execution/Exec_sysmon_meterpreter_reversetcp_msipackage.evtx',
     '328ec1b4b6c531af991a2de2221900ec93db1853f7446f61c7e3c9bf9bf052e3'),
]
SYSMON = {'1': 'Process create', '2': 'File creation time changed', '3': 'Network connection',
          '10': 'Process access', '13': 'Registry value set', '18': 'Pipe connected', '7': 'Image loaded'}

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(65536), b''):
            h.update(b)
    return h.hexdigest()

def summarise(eid, d):
    g = lambda k: d.get(k, '')
    if eid == '1':
        return f"{g('ParentImage').split(chr(92))[-1]} -> {g('Image').split(chr(92))[-1]} | {g('CommandLine')[:90]} | user={g('User')}"
    if eid == '3':
        return f"{g('Image').split(chr(92))[-1]} {'OUT' if g('Initiated')=='True' else 'IN'} {g('SourceIp')}:{g('SourcePort')} -> {g('DestinationIp')}:{g('DestinationPort')}"
    if eid == '13':
        return f"{g('Image').split(chr(92))[-1]} set {g('TargetObject')} = {g('Details')[:60]}"
    if eid == '2':
        return f"{g('Image').split(chr(92))[-1]} changed creation time of {g('TargetFilename')} ({g('PreviousCreationUtcTime')} -> {g('CreationUtcTime')})"
    if eid == '10':
        return f"{g('SourceImage').split(chr(92))[-1]}(pid {g('SourceProcessId')}) opened {g('TargetImage').split(chr(92))[-1]}(pid {g('TargetProcessId')}) access={g('GrantedAccess')}"
    if eid == '18':
        return f"{g('Image')} pipe {g('PipeName')}"
    if eid == '7':
        return f"{g('Image').split(chr(92))[-1]} loaded {g('ImageLoaded')}"
    return ''

def main(root, out):
    os.makedirs(out, exist_ok=True)
    rows, log = [], []
    for label, rel, want in EVIDENCE:
        p = os.path.join(root, rel); got = sha256(p)
        ok = 'MATCH' if got == want else 'MISMATCH'
        log.append((label, rel, os.path.getsize(p), got, ok))
        if ok != 'MATCH':
            sys.exit(f'Hash mismatch for {rel}: {got}')
        with evtx.Evtx(p) as f:
            for rec in f.records():
                r = etree.fromstring(rec.xml().encode()); s = r.find('e:System', NS)
                eid = s.find('e:EventID', NS).text
                d = {x.get('Name'): (x.text or '') for x in r.iter('{%s}Data' % NS['e'])}
                rows.append({
                    'source': label, 'record_id': s.find('e:EventRecordID', NS).text, 'eid': eid,
                    'type': SYSMON.get(eid, eid), 'host': s.find('e:Computer', NS).text,
                    'event_utc': d.get('UtcTime', ''),
                    'record_utc': s.find('e:TimeCreated', NS).get('SystemTime')[:23],
                    'summary': summarise(eid, d)})
    rows.sort(key=lambda r: (r['event_utc'], r['record_id']))
    for i, r in enumerate(rows, 1):
        r['id'] = f'T{i:02d}'
        # delay between event time and when Sysmon wrote the record (seconds)
        from datetime import datetime
        a = datetime.fromisoformat(r['event_utc']); b = datetime.fromisoformat(r['record_utc'])
        r['log_delay_s'] = round((b - a).total_seconds(), 3)
    cols = ['id', 'source', 'record_id', 'eid', 'type', 'event_utc', 'record_utc', 'log_delay_s', 'host', 'summary']
    with open(os.path.join(out, 'timeline.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    with open(os.path.join(out, 'evidence_log.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['label', 'file', 'bytes', 'sha256', 'hash_check']); w.writerows(log)
    print(f'{len(rows)} events; hashes verified for {len(log)} files')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
