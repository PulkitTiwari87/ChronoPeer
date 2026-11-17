#!/usr/bin/env python3
"""Build the static site for DF-PBL-040 from the project's CSV files.

Usage (from the project folder):  python3 -I site/build_site.py
Reads the six CSVs next to this folder, writes site/index.html and copies the
derived CSVs plus build_timeline.py into site/data/ for download.
Every fact on the page comes from those files; nothing is typed in by hand
except the explanatory wording. README.md and the deck are never read.
"""
import csv
import datetime as dt
import html
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NL = chr(10)
esc = html.escape


def rows(name):
    with open(os.path.join(ROOT, name), newline="", encoding="utf8") as f:
        return list(csv.DictReader(f))


timeline = rows("timeline.csv")
evidence = rows("evidence_log.csv")
v1 = rows("inference_register.csv")
v2 = {r["id"]: r for r in rows("inference_register_v2.csv")}
critique = rows("peer_critique.csv")
revisions = rows("revision_log.csv")

# ---------- derived numbers ----------
n_events = len(timeline)
n_files = len(evidence)
n_infer = len(v1)
NUMBER_WORDS = {9: "nine"}
n_infer_word = NUMBER_WORDS.get(n_infer, str(n_infer))
changed_rows = [r for r in revisions
                if r["revision"].startswith("R1")
                and r["decision"] != "Answered"
                and not r["change_made"].startswith("No rating change")]
n_changed = len(changed_rows)

by_src = {}
for r in timeline:
    by_src.setdefault(r["source"], []).append(r)
ids = {s: sorted(int(r["record_id"]) for r in v) for s, v in by_src.items()}
gap_ab = ids["B"][0] - ids["A"][-1] - 1
gap_bc = ids["C"][0] - ids["B"][-1] - 1

epoch = 1556656369
epoch_utc = dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
t11 = [r for r in timeline if r["id"] == "T11"][0]["event_utc"][11:23]

GROUPS = {
    "A": ("Remote service starts hidden PowerShell",
          "SMB in from 10.0.2.19; a service named hello starts hidden PowerShell, which connects out to 10.0.2.19:4444."),
    "B": ("Remote command runs whoami as a user",
          "SMB in; WmiPrvSE starts cmd.exe as IEUser and runs whoami /all, writing output to ADMIN$."),
    "C": ("Installer package opens a command prompt",
          "msiexec runs a package from the user's Temp folder; MSI4FFD.tmp starts cmd.exe; whoami runs three minutes later."),
}


def chip(text, kind=None):
    if kind is None:
        first = text.strip().split(" ")[0].strip("(;,/").lower()
        kind = first if first in ("high", "medium", "low", "rejected") else "neutral"
    return '<span class="chip chip-%s">%s</span>' % (kind, esc(text))


def outcome_chip(text):
    low = text.lower()
    kind = "partly" if low.startswith("partly") else ("answered" if low.startswith("answered") else "upheld")
    return '<span class="chip chip-%s">%s</span>' % (kind, esc(text))


# ---------- sections ----------
def stats():
    items = [(n_events, "events in the timeline"), (n_files, "evidence files, hashed"),
             (n_infer, "inferences drawn"), (n_changed, "changed after review")]
    return NL.join('<div class="stat"><div class="stat-n">%d</div><div class="stat-l">%s</div></div>' % i for i in items)


STEPS = [
    ("Verify", "Recompute the SHA-256 of every file. The script stops on a mismatch."),
    ("Parse", "Read the Sysmon events from the three EVTX files."),
    ("Order", "Sort by the event time Sysmon logged, not by record order."),
    ("Number", "Label events T01 to T%02d and write inferences I1 to I%d." % (n_events, n_infer)),
    ("Challenge", "A reviewer gives an alternative explanation for each inference."),
    ("Revise", "Change the claim, and log every decision with its reason."),
]


def steps():
    out = []
    for i, (h, p) in enumerate(STEPS, 1):
        out.append('<li class="card step reveal"><span class="step-n">%02d</span><h3>%s</h3><p>%s</p></li>' % (i, esc(h), esc(p)))
    return NL.join(out)


def timeline_groups():
    out = []
    for s in sorted(by_src):
        ev = by_src[s]
        title, desc = GROUPS.get(s, ("", ""))
        fname = [e["file"].split("/")[-1] for e in evidence if e["label"] == s]
        span = "%s to %s UTC" % (ev[0]["event_utc"][11:19], ev[-1]["event_utc"][11:19])
        lines = []
        for r in ev:
            lines.append(
                '<li class="ev"><span class="ev-id">%s</span><span class="ev-t">%s</span>'
                '<span class="ev-type">%s</span><span class="ev-sum">%s</span></li>'
                % (esc(r["id"]), esc(r["event_utc"][11:23]), esc(r["type"]), esc(r["summary"])))
        out.append(
            '<article class="card group reveal" data-src="%s">'
            '<header class="group-h"><span class="badge" aria-hidden="true">%s</span><div>'
            '<h3>%s</h3><p class="muted">%s &middot; %s &middot; %d events &middot; host %s</p></div></header>'
            '<p class="group-d">%s</p>'
            '<p class="file mono">%s</p>'
            '<ol class="evs">%s</ol></article>'
            % (esc(s), esc(s), esc(title), esc(ev[0]["event_utc"][:10]), esc(span), len(ev), esc(ev[0]["host"]),
               esc(desc), esc(fname[0] if fname else ""), NL.join(lines)))
    return NL.join(out)


def inferences():
    out = []
    for r in v1:
        i = r["id"]
        n = v2[i]
        change = n["change_from_v1"]
        changed = change.strip().lower() != "unchanged"
        tag = '<span class="chip %s">%s</span>' % ("chip-changed" if changed else "chip-neutral", esc(change))
        out.append(
            '<article class="card infer reveal">'
            '<header class="infer-h"><span class="infer-id mono">%s</span>%s</header>'
            '<div class="cols"><div><p class="label">Before review</p><p>%s</p>%s</div>'
            '<div><p class="label">After review</p><p>%s</p>%s</div></div>'
            '<details><summary>The author&rsquo;s own alternative and what is not shown</summary>'
            '<dl><dt>Supporting events</dt><dd>%s</dd>'
            '<dt>Alternative anticipated by the author</dt><dd>%s</dd>'
            '<dt>Evidence that tells them apart</dt><dd>%s</dd>'
            '<dt>Cannot be shown by these logs</dt><dd>%s</dd></dl></details></article>'
            % (esc(i), tag, esc(r["inference (v1, author)"]), chip(r["confidence_v1"]),
               esc(n["inference (v2, after review)"]), chip(n["confidence_v2"]),
               esc(r["supporting_events"]), esc(r["alternative_anticipated_by_author"]),
               esc(r["discriminating_evidence"]), esc(r["cannot_be_shown_by_these_logs"])))
    return NL.join(out)


def challenges():
    out = []
    for r in critique:
        out.append(
            '<article class="card chal reveal"><header class="chal-h"><span class="infer-id mono">%s</span>%s</header>'
            '<p class="label">Reviewer&rsquo;s challenge</p><p class="chal-q">%s</p>'
            '<p class="label">What the logs show</p><p>%s</p>'
            '<p class="label">What would tell them apart</p><p>%s</p>'
            '<footer class="chal-f"><span class="muted">Challenge strength: %s</span>'
            '<span class="muted">%s &middot; %s</span></footer></article>'
            % (esc(r["item"]), outcome_chip(r["outcome"]), esc(r["reviewer_challenge"]),
               esc(r["evidence_in_logs"]), esc(r["evidence_that_would_distinguish"]),
               esc(r["challenge_strength (Supported/Weak/Unsupported)"]), esc(r["reviewer"]), esc(r["date"])))
    return NL.join(out)


def revision_table():
    body = []
    for r in revisions:
        body.append(
            '<tr><td data-label="Rev"><strong>%s</strong><br><span class="muted">%s</span></td>'
            '<td data-label="Item" class="mono">%s</td><td data-label="Issue">%s</td>'
            '<td data-label="Decision">%s</td><td data-label="Change made">%s</td><td data-label="By">%s</td></tr>'
            % (esc(r["revision"]), esc(r["stage"]), esc(r["item"]), esc(r["challenge_or_issue"]),
               esc(r["decision"]), esc(r["change_made"]), esc(r["by"])))
    return NL.join(body)


LIMITS = [
    ("Excerpts, not full logs",
     "%d record IDs are missing between files A and B, and %d between B and C. Absence of an event is not evidence of absence." % (gap_ab, gap_bc)),
    ("Sysmon only", "There is no Security log, so no record of which account authenticated, and no packet capture, so no payload content."),
    ("Labelled lab data", "File names such as meterpreter and psexec can bias the reading. They were treated as labels, not evidence."),
    ("One AI reviewer", "The reviewer was an AI. It shows where the reasoning is weak, not that the rest is safe. I8 and I9 were challenged in a later pass. A human reviewer can add a second round."),
]


def limits():
    return NL.join('<li class="card reveal"><h3>%s</h3><p>%s</p></li>' % (esc(h), esc(p)) for h, p in LIMITS)


def evidence_rows():
    out = []
    for e in evidence:
        out.append(
            '<li class="evid"><span class="badge badge-dark" aria-hidden="true">%s</span><div class="evid-main">'
            '<p class="evid-f">%s</p><p class="mono evid-h">%s</p><p class="evid-b">%s bytes</p></div>%s</li>'
            % (esc(e["label"]), esc(e["file"]), esc(e["sha256"]), esc(e["bytes"]),
               '<span class="chip chip-match">%s</span>' % esc(e["hash_check"])))
    return NL.join(out)


DATA_FILES = ["timeline.csv", "evidence_log.csv", "inference_register.csv", "inference_register_v2.csv",
              "peer_critique.csv", "revision_log.csv", "build_timeline.py"]


def downloads():
    return NL.join('<li><a class="link" href="data/%s" download>%s</a></li>' % (esc(f), esc(f)) for f in DATA_FILES)


CSS = """
:root{--bg:#fff;--bg2:#f5f5f7;--text:#1d1d1f;--muted:#6e6e73;--line:rgba(0,0,0,.14);--accent:#0071e3;--accent-hi:#0077ed;--on-accent:#fff;
--card:#f5f5f7;--nav:rgba(255,255,255,.72);--ok-bg:rgba(52,199,89,.16);--ok:#1a7f37;--warn-bg:rgba(255,159,10,.18);--warn:#8a5300;
--bad-bg:rgba(255,59,48,.14);--bad:#c5221f;--neu-bg:rgba(120,120,128,.16);--neu:#515154;--tint-bg:rgba(0,113,227,.12);--tint:#0060c0;
--font:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Pro Display","Segoe UI",Roboto,Helvetica,Arial,sans-serif;
--mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#000;--bg2:#161617;--text:#f5f5f7;--muted:#a1a1a6;--line:rgba(255,255,255,.18);--accent:#2997ff;--accent-hi:#47a5ff;
--card:#1d1d1f;--nav:rgba(22,22,23,.72);--ok-bg:rgba(48,209,88,.18);--ok:#30d158;--warn-bg:rgba(255,214,10,.16);--warn:#ffd60a;
--bad-bg:rgba(255,105,97,.18);--bad:#ff6961;--neu-bg:rgba(235,235,245,.16);--neu:#c7c7cc;--tint-bg:rgba(41,151,255,.18);--tint:#64b5ff}}
*{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%;scroll-padding-top:64px}
body{margin:0;background:var(--bg);color:var(--text);font:400 1rem/1.5 var(--font);-webkit-font-smoothing:antialiased;overflow-wrap:break-word}
a{color:inherit}
.mono{font-family:var(--mono);font-size:.92em}
.muted{color:var(--muted)}
.skip{position:absolute;left:-999px;top:8px;background:var(--accent);color:var(--on-accent);padding:8px 14px;border-radius:999px;z-index:20}
.skip:focus{left:16px}
:focus-visible{outline:3px solid var(--accent);outline-offset:3px;border-radius:8px}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
.nav{position:sticky;top:0;z-index:10;background:var(--nav);-webkit-backdrop-filter:saturate(180%) blur(20px);backdrop-filter:saturate(180%) blur(20px);border-bottom:1px solid var(--line)}
.nav-in{display:flex;align-items:center;gap:24px;height:52px}
.nav-title{font-weight:600;letter-spacing:-.01em;white-space:nowrap;text-decoration:none}
.nav-links{display:flex;gap:4px;margin-left:auto;overflow-x:auto;scrollbar-width:none}
.nav-links::-webkit-scrollbar{display:none}
.nav-links a{font-size:.8125rem;color:var(--muted);text-decoration:none;padding:6px 12px;border-radius:999px;white-space:nowrap}
.nav-links a:hover{color:var(--text);background:var(--neu-bg)}
section{padding:clamp(72px,12vw,128px) 0}
.alt{background:var(--bg2);--card:var(--bg)}
.eyebrow{font-size:.75rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 16px}
h1,h2,h3{margin:0;font-weight:600;text-wrap:balance}
h1{font-size:clamp(2.5rem,8vw,5rem);line-height:1.04;letter-spacing:-.035em}
h2{font-size:clamp(2rem,5vw,3.5rem);line-height:1.08;letter-spacing:-.03em}
h3{font-size:1.25rem;line-height:1.25;letter-spacing:-.01em}
.lede{font-size:clamp(1.1rem,2.2vw,1.5rem);line-height:1.4;color:var(--muted);max-width:44ch;margin:24px 0 0;letter-spacing:-.005em;text-wrap:pretty}
.sec-h{margin-bottom:clamp(40px,6vw,64px)}
.sec-h .lede{font-size:1.125rem;max-width:56ch}
.hero{padding-top:clamp(64px,10vw,120px);padding-bottom:clamp(56px,8vw,96px);text-align:center}
.hero .wrap{display:flex;flex-direction:column;align-items:center}
.hero h1{max-width:14ch}
.hero .lede{max-width:34ch}
.cta{display:flex;flex-wrap:wrap;gap:12px 28px;justify-content:center;align-items:center;margin-top:36px}
.btn{display:inline-block;background:var(--accent);color:var(--on-accent);text-decoration:none;padding:12px 24px;border-radius:999px;border:0;font:inherit;font-weight:500;cursor:pointer;transition:transform 100ms ease-out,background-color 100ms ease-out}
.btn:hover{background:var(--accent-hi)}
.btn:active,.seg button:active{transform:scale(.97)}
.link{color:var(--accent);text-decoration:none}
.link:hover{text-decoration:underline}
.link.chev::after{content:" ›"}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;margin-top:clamp(48px,8vw,88px);width:100%;max-width:880px}
.stat-n{font-size:clamp(2.5rem,6vw,4rem);font-weight:600;letter-spacing:-.035em;line-height:1}
.stat-l{color:var(--muted);font-size:.9375rem;margin-top:8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:24px;padding:28px}
.card p{margin:0}
.steps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}
.step h3{margin:12px 0 8px}
.step p{color:var(--muted);font-size:.9375rem}
.step-n{font-family:var(--mono);font-size:.8125rem;color:var(--accent);font-weight:600}
.seg{display:none;gap:4px;background:var(--neu-bg);padding:4px;border-radius:999px;width:max-content;max-width:100%;margin-bottom:28px}
.js .seg{display:flex}
.seg button{font:inherit;font-size:.875rem;font-weight:500;background:transparent;color:var(--text);border:0;padding:7px 18px;border-radius:999px;cursor:pointer;transition:transform 100ms ease-out,background-color 100ms ease-out}
.seg button[aria-pressed=true]{background:var(--bg);box-shadow:0 1px 3px rgba(0,0,0,.18)}
.groups{display:grid;grid-template-columns:minmax(0,1fr);gap:20px}
.group[hidden]{display:none}
.group-h{display:flex;gap:16px;align-items:center}
.badge{flex:none;width:48px;height:48px;border-radius:50%;background:var(--accent);color:var(--on-accent);display:grid;place-items:center;font-weight:600;font-size:1.25rem}
.badge-dark{width:36px;height:36px;font-size:1rem;background:#2d2d2f;color:#f5f5f7}
.group-h .muted{font-size:.875rem;margin-top:4px}
.group-d{margin:20px 0 6px!important}
.file{color:var(--muted);font-size:.8125rem!important;margin-bottom:16px!important;overflow-wrap:anywhere}
.evs{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
.ev{display:grid;grid-template-columns:48px 108px 150px 1fr;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);font-size:.9rem;align-items:baseline}
.ev:last-child{border-bottom:0}
.ev-id{font-family:var(--mono);font-weight:600;color:var(--accent)}
.ev-t{font-family:var(--mono);color:var(--muted);font-size:.8125rem}
.ev-type{color:var(--muted);font-size:.8125rem}
.ev-sum{font-family:var(--mono);font-size:.8125rem;overflow-wrap:anywhere}
.chip{display:inline-block;font-size:.75rem;font-weight:600;padding:4px 12px;border-radius:999px;line-height:1.4;max-width:100%}
.chip-high,.chip-match{background:var(--ok-bg);color:var(--ok)}
.chip-medium,.chip-partly{background:var(--warn-bg);color:var(--warn)}
.chip-low,.chip-neutral{background:var(--neu-bg);color:var(--neu)}
.chip-rejected{background:var(--bad-bg);color:var(--bad)}
.chip-changed,.chip-upheld{background:var(--tint-bg);color:var(--tint)}
.chip-answered{background:var(--ok-bg);color:var(--ok)}
.stack{display:grid;grid-template-columns:minmax(0,1fr);gap:16px}
.infer-h,.chal-h{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:20px}
.infer-id{font-size:1.5rem;font-weight:600;letter-spacing:-.02em}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:28px}
.cols p:not(.label){margin-bottom:12px}
.label{font-size:.75rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 6px!important}
.chal .label{margin-top:18px!important}
.chal-q{font-size:1.125rem;line-height:1.4;letter-spacing:-.01em;font-weight:500}
.chal-f{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px 16px;margin-top:22px;padding-top:16px;border-top:1px solid var(--line);font-size:.8125rem}
details{margin-top:20px;border-top:1px solid var(--line);padding-top:16px}
summary{cursor:pointer;color:var(--accent);font-size:.9375rem;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"›";display:inline-block;margin-right:8px;transition:transform 150ms ease-out}
details[open] summary::before{transform:rotate(90deg)}
dl{margin:16px 0 0;display:grid;gap:14px}
dt{font-size:.75rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
dd{margin:4px 0 0}
.tablecard{padding:8px 8px 0;overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{text-align:left;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600;padding:14px 16px;border-bottom:1px solid var(--line)}
td{padding:14px 16px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
.limits{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}
.limits h3{margin-bottom:10px}
.limits p{color:var(--muted);font-size:.9375rem}
.dark{background:#000;color:#f5f5f7;--line:rgba(255,255,255,.18);--muted:#a1a1a6;--card:#1d1d1f;--accent:#2997ff}
.dark .eyebrow{color:#a1a1a6}
.code{background:#1d1d1f;border:1px solid var(--line);border-radius:20px;padding:22px 24px;font-family:var(--mono);font-size:.9rem;line-height:1.7;overflow-x:auto;margin:0 0 28px}
.code .p{color:#a1a1a6}
.code .o{color:#30d158}
.evlist{list-style:none;margin:0 0 28px;padding:0;display:grid;gap:12px}
.evid{display:flex;gap:16px;align-items:center;background:#1d1d1f;border:1px solid var(--line);border-radius:20px;padding:16px 20px}
.evid-main{flex:1;min-width:0}
.evid-f{margin:0;font-weight:500;overflow-wrap:anywhere}
.evid-h{margin:4px 0 0;color:#a1a1a6;overflow-wrap:anywhere;font-size:.75rem}
.evid-b{margin:2px 0 0;color:#a1a1a6;font-size:.75rem}
.dark .chip-match{background:rgba(48,209,88,.18);color:#30d158}
.note{color:#a1a1a6;font-size:.9375rem;max-width:68ch;margin:0 0 12px}
.dl{list-style:none;padding:0;margin:28px 0 0;display:flex;flex-wrap:wrap;gap:8px 24px}
footer.site{background:var(--bg2);padding:40px 0 56px;color:var(--muted);font-size:.8125rem}
footer.site p{max-width:78ch;margin:0 0 8px}
.js .reveal{opacity:0;transform:translateY(14px);transition:opacity 500ms ease-out,transform 500ms ease-out}
.js .reveal.in{opacity:1;transform:none}
@media (max-width:760px){
.stats{grid-template-columns:repeat(2,1fr)}
.cols{grid-template-columns:1fr;gap:4px}
.ev{grid-template-columns:44px 1fr;gap:2px 12px}
.ev-t{grid-column:2}.ev-type{grid-column:2}.ev-sum{grid-column:1/-1;margin-top:4px}
.nav-in{gap:12px}
thead{display:none}
table,tbody,tr,td{display:block}
tr{padding:14px 12px;border-bottom:1px solid var(--line)}tr:last-child{border-bottom:0}
td{border:0;padding:6px 4px}
td::before{content:attr(data-label);display:block;font-size:.7rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.evid{align-items:flex-start;flex-wrap:wrap}
}
@media (prefers-reduced-motion:reduce){
html{scroll-behavior:auto}
.js .reveal{opacity:1;transform:none;transition:none}
.btn,.seg button,summary::before{transition:none}
details[open] summary::before{transform:none}
}
@media (prefers-reduced-transparency:reduce){.nav{background:var(--bg);-webkit-backdrop-filter:none;backdrop-filter:none}}
@media (prefers-contrast:more){:root{--line:rgba(0,0,0,.5)}.card{border-width:2px}}
@media (prefers-contrast:more) and (prefers-color-scheme:dark){:root{--line:rgba(255,255,255,.6)}}
"""

JS = """
(function(){
var d=document;
var seg=d.getElementById('seg');
if(seg){seg.addEventListener('click',function(e){
var b=e.target.closest('button');if(!b)return;
var f=b.getAttribute('data-f');
seg.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});
d.querySelectorAll('.group').forEach(function(g){g.hidden=!(f==='all'||g.getAttribute('data-src')===f)});
});}
var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
var els=d.querySelectorAll('.reveal');
if(reduce||!('IntersectionObserver' in window)){els.forEach(function(el){el.classList.add('in')});return;}
var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting){en.target.classList.add('in');io.unobserve(en.target)}})},{rootMargin:'0px 0px -8% 0px'});
els.forEach(function(el){io.observe(el)});
})();
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Incident Timeline Peer Review</title>
<meta name="description" content="A forensic timeline of @@N_EVENTS@@ events on one Windows host, @@N_INFER@@ inferences drawn from it, and an alternative explanation for each one.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='14' fill='%230071e3'/%3E%3C/svg%3E">
<script>document.documentElement.className='js'</script>
<style>@@CSS@@</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="nav"><div class="wrap nav-in">
<a class="nav-title" href="#top">Incident Timeline</a>
<nav class="nav-links" aria-label="Sections">
<a href="#timeline">Timeline</a><a href="#inferences">Inferences</a><a href="#challenges">Challenges</a><a href="#revisions">Revisions</a><a href="#limits">Limits</a><a href="#reproduce">Reproduce</a>
</nav></div></header>
<main id="main">
<section class="hero" id="top"><div class="wrap">
<p class="eyebrow">Digital forensics case study &middot; DF-PBL-040</p>
<h1>Read the logs. Challenge every conclusion.</h1>
<p class="lede">A timeline of @@N_EVENTS@@ events on one Windows host, @@N_INFER@@ inferences drawn from it, and an alternative explanation for each one.</p>
<div class="cta"><a class="btn" href="#timeline">See the timeline</a><a class="link chev" href="#reproduce">How it was verified</a></div>
<div class="stats">@@STATS@@</div>
</div></section>

<section class="alt" id="how"><div class="wrap">
<div class="sec-h"><p class="eyebrow">Method</p><h2>Six steps. Each one repeatable.</h2></div>
<ol class="steps">@@STEPS@@</ol>
</div></section>

<section id="timeline"><div class="wrap">
<div class="sec-h"><p class="eyebrow">Original timeline</p><h2>Three bursts of activity on one host.</h2>
<p class="lede">Event times are the UTC times Sysmon logged. This is what the logs show, before any interpretation.</p></div>
<div class="seg" id="seg" role="group" aria-label="Filter by evidence file">
<button type="button" data-f="all" aria-pressed="true">All</button><button type="button" data-f="A" aria-pressed="false">A</button><button type="button" data-f="B" aria-pressed="false">B</button><button type="button" data-f="C" aria-pressed="false">C</button></div>
<div class="groups">@@GROUPS@@</div>
</div></section>

<section class="alt" id="inferences"><div class="wrap">
<div class="sec-h"><p class="eyebrow">Inference register</p><h2>@@N_INFER_WORD@@ conclusions. Narrower after review.</h2>
<p class="lede">Each inference has a confidence level. High means the log shows it directly. Low means a simpler, harmless explanation fits the same events.</p></div>
<div class="stack">@@INFER@@</div>
</div></section>

<section id="challenges"><div class="wrap">
<div class="sec-h"><p class="eyebrow">Peer critique</p><h2>Every inference gets an alternative.</h2>
<p class="lede">The reviewer is an AI (Claude), so this is a critique round, not a human peer. @@CHAL_COUNT@@ items were challenged and answered against the events.</p></div>
<div class="stack">@@CHAL@@</div>
</div></section>

<section class="alt" id="revisions"><div class="wrap">
<div class="sec-h"><p class="eyebrow">Revision log</p><h2>Every change has a reason.</h2></div>
<div class="card tablecard reveal"><table><thead><tr><th>Rev</th><th>Item</th><th>Issue</th><th>Decision</th><th>Change made</th><th>By</th></tr></thead><tbody>@@REV@@</tbody></table></div>
</div></section>

<section id="limits"><div class="wrap">
<div class="sec-h"><p class="eyebrow">Limitations</p><h2>What these logs cannot show.</h2></div>
<ul class="limits">@@LIMITS@@</ul>
</div></section>

<section class="dark" id="reproduce"><div class="wrap">
<div class="sec-h"><p class="eyebrow">Reproducible test</p><h2>Run it. Get the same @@N_EVENTS@@ events.</h2></div>
<pre class="code"><span class="p">$</span> python3 -I build_timeline.py EVTX-ATTACK-SAMPLES out/
<span class="o">@@N_EVENTS@@ events; hashes verified for @@N_FILES@@ files</span></pre>
<ul class="evlist">@@EVID@@</ul>
<p class="note">Independent cross-check: the output file name __@@EPOCH@@ decodes to @@EPOCH_UTC@@ UTC. Sysmon logged the matching connection (T11) at @@T11@@.</p>
<p class="note">Re-run from the pinned dataset commit: the regenerated timeline.csv and evidence_log.csv were byte-identical to the files published here.</p>
<ul class="dl">@@DOWNLOADS@@</ul>
</div></section>
</main>
<footer class="site"><div class="wrap">
<p>Dataset: sbousseaden/EVTX-ATTACK-SAMPLES (GPL-3.0), commit 4ceed2f. Educational lab data from host IEWIN7, 30 April 2019.</p>
<p>Tools: Python 3, python-evtx, lxml. AI assistance: the script, registers and slides were drafted with Claude, and the review rounds were performed by Claude acting as a reviewer.</p>
</div></footer>
<script>@@JS@@</script>
</body>
</html>
"""


def main():
    subs = {
        "@@CSS@@": CSS, "@@JS@@": JS,
        "@@N_EVENTS@@": str(n_events), "@@N_INFER@@": n_infer_word,
        "@@N_INFER_WORD@@": n_infer_word.capitalize(), "@@N_FILES@@": str(n_files),
        "@@STATS@@": stats(), "@@STEPS@@": steps(), "@@GROUPS@@": timeline_groups(), "@@INFER@@": inferences(),
        "@@CHAL@@": challenges(), "@@CHAL_COUNT@@": str(len(critique)), "@@REV@@": revision_table(),
        "@@LIMITS@@": limits(), "@@EVID@@": evidence_rows(), "@@EPOCH@@": str(epoch), "@@EPOCH_UTC@@": epoch_utc,
        "@@T11@@": t11, "@@DOWNLOADS@@": downloads(),
    }
    page = PAGE
    for k, v in subs.items():
        page = page.replace(k, v)
    assert "@@" not in page, "unreplaced placeholder"
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    for f in DATA_FILES:
        shutil.copyfile(os.path.join(ROOT, f), os.path.join(HERE, "data", f))
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf8", newline="") as fh:
        fh.write(page)
    print("wrote site/index.html (%d bytes); events=%d infer=%d changed=%d gaps=%d/%d" %
          (len(page.encode("utf8")), n_events, n_infer, n_changed, gap_ab, gap_bc))


if __name__ == "__main__":
    main()
