import { useRef, useState } from "react";
import { api } from "../services/api";
import EvidenceTable from "../components/EvidenceTable";
import StatusBadge from "../components/StatusBadge";
import { Btn, Card, Chip, Field, Loading, NeedRole, NoCase, Notice, PageTitle, inputCls, useApp, useLoad } from "../components/ui";

export default function EvidenceUpload() {
  const { caseId } = useApp();
  const evidence = useLoad(() => (caseId ? api.evidence(caseId) : Promise.resolve([])), [caseId]);
  const fileRef = useRef(null);
  const [tzMode, setTzMode] = useState("");
  const [tzCustom, setTzCustom] = useState("+05:30");
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [state, setState] = useState({ busy: false, error: null });
  const tz = tzMode === "custom" ? tzCustom : tzMode;

  const run = async (kind) => {
    const file = fileRef.current?.files?.[0];
    if (!file) return setState({ busy: false, error: "Choose a CSV or JSON file first." });
    setState({ busy: true, error: null });
    try {
      if (kind === "preview") {
        setResult(null);
        setPreview(await api.previewEvidence(caseId, file, tz));
      } else {
        setResult(await api.importEvidence(caseId, file, tz));
        setPreview(null);
        fileRef.current.value = "";
        evidence.reload();
      }
      setState({ busy: false, error: null });
    } catch (e) {
      setState({ busy: false, error: e.message });
    }
  };

  if (!caseId) return <><PageTitle eyebrow="Evidence" title="Import evidence" /><NoCase /></>;
  return (
    <>
      <PageTitle
        eyebrow="Evidence"
        title="Import evidence"
        lede="Upload a normalised CSV or JSON export. The file is hashed with SHA-256 and stored untouched; its records are validated and added to the timeline."
      />
      <NeedRole role="investigator">
        <Card>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Field label="Evidence file (.csv or .json)" hint="Columns: timestamp, event_type, description, source, artifact_id.">
                <input ref={fileRef} type="file" accept=".csv,.json" className={inputCls} onChange={() => { setPreview(null); setResult(null); }} />
              </Field>
            </div>
            <Field label="Timestamps without a timezone" hint="Unknown timezones are never converted silently. Choose an assumption only if you know it.">
              <select className={inputCls} value={tzMode} onChange={(e) => setTzMode(e.target.value)}>
                <option value="">Keep as unknown (recommended)</option>
                <option value="UTC">Assume UTC</option>
                <option value="custom">Assume a fixed offset…</option>
              </select>
            </Field>
            {tzMode === "custom" && <Field label="Offset"><input className={inputCls} value={tzCustom} onChange={(e) => setTzCustom(e.target.value)} placeholder="+05:30" /></Field>}
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Btn onClick={() => run("preview")} disabled={state.busy}>Preview</Btn>
            <Btn variant="secondary" onClick={() => run("import")} disabled={state.busy || !preview || preview.already_imported || preview.valid_records === 0}>
              Confirm import
            </Btn>
          </div>
          {state.error && <div className="mt-4"><Notice kind="bad">{state.error}</Notice></div>}
          {preview && (
            <div className="mt-6 space-y-4">
              {preview.already_imported && <Notice kind="warn">This exact file (same SHA-256) is already in this investigation.</Notice>}
              <div className="flex flex-wrap gap-2 text-sm">
                <Chip kind="ok">{preview.valid_records} valid records</Chip>
                <Chip kind={preview.malformed_count ? "bad" : "neutral"}>{preview.malformed_count} malformed</Chip>
                <Chip>{preview.duplicate_records_skipped} duplicates skipped</Chip>
                {Object.entries(preview.by_timezone_status).map(([k, v]) => <Chip key={k} kind={k === "known" ? "ok" : "warn"}>{v} {k} timezone</Chip>)}
              </div>
              <p className="font-mono text-xs [overflow-wrap:anywhere]">SHA-256 {preview.sha256}</p>
              {preview.malformed.length > 0 && <ul className="list-disc pl-5 text-sm text-bad">{preview.malformed.slice(0, 8).map((m) => <li key={m.row}>Row {m.row}: {m.reason}</li>)}</ul>}
              <div className="scroll-x">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead><tr className="text-xs uppercase tracking-wider text-muted">{["Row", "Original", "UTC", "Timezone", "Type", "Artifact", "Description"].map((h) => <th key={h} className="border-b border-line px-3 py-2 font-semibold">{h}</th>)}</tr></thead>
                  <tbody>
                    {preview.sample.map((s) => (
                      <tr key={s.row} className="align-top">
                        <td className="border-b border-line px-3 py-2">{s.row}</td>
                        <td className="border-b border-line px-3 py-2 font-mono text-xs">{s.timestamp || "—"}</td>
                        <td className="border-b border-line px-3 py-2 font-mono text-xs">{s.utc || "—"}</td>
                        <td className="border-b border-line px-3 py-2"><StatusBadge value={s.timezone_status} /></td>
                        <td className="border-b border-line px-3 py-2">{s.event_type}</td>
                        <td className="border-b border-line px-3 py-2">{s.artifact_id}</td>
                        <td className="border-b border-line px-3 py-2">{s.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {preview.valid_records > preview.sample.length && <p className="text-xs text-muted">Showing the first {preview.sample.length} records.</p>}
            </div>
          )}
          {result && <div className="mt-5"><Notice kind="ok">Imported {result.valid_records} events from {result.filename}. SHA-256 {result.sha256.slice(0, 16)}… recorded.</Notice></div>}
        </Card>
      </NeedRole>
      <h2 className="mb-4 mt-12 text-2xl font-semibold tracking-tight">Evidence inventory</h2>
      <Card>
        <Loading error={evidence.error} loading={evidence.loading && !evidence.data} />
        {evidence.data && <EvidenceTable evidence={evidence.data} />}
      </Card>
    </>
  );
}
