import { useMemo, useState } from "react";
import { api } from "../services/api";
import StatusBadge from "../components/StatusBadge";
import Timeline from "../components/Timeline";
import { Btn, Card, Chip, Loading, NoCase, PageTitle, fmtUtc, inputCls, useApp, useLoad } from "../components/ui";

export default function TimelinePage() {
  const { caseId } = useApp();
  const [order, setOrder] = useState("asc");
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const { data, error, loading } = useLoad(() => (caseId ? api.timeline(caseId, order) : Promise.resolve(null)), [caseId, order]);

  const types = useMemo(() => (data ? [...new Set(data.events.map((e) => e.event_type))] : []), [data]);
  const shown = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.events.filter(
      (e) => (!type || e.event_type === type) && (!q || `${e.description} ${e.artifact_reference} ${e.source}`.toLowerCase().includes(q)),
    );
  }, [data, query, type]);

  if (!caseId) return <><PageTitle eyebrow="Timeline" title="Incident timeline" /><NoCase /></>;
  return (
    <>
      <PageTitle
        eyebrow="Timeline"
        title="Incident timeline"
        lede="Events in chronological order. The same input always produces the same order; events without a usable UTC time are listed last and flagged."
      />
      <Loading error={error} loading={loading && !data} />
      {data && (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-2 text-sm">
            <Chip>{data.summary.total} events</Chip>
            {Object.entries(data.summary.by_timezone_status).filter(([, n]) => n > 0).map(([k, n]) => <Chip key={k} kind={k === "known" ? "ok" : "warn"}>{n} {k}</Chip>)}
          </div>
          <Card className="mb-8"><Timeline events={data.events} /></Card>
          <Card>
            <div className="mb-5 flex flex-wrap items-end gap-3">
              <input aria-label="Search events" className={`${inputCls} max-w-xs`} placeholder="Search description or artifact" value={query} onChange={(e) => setQuery(e.target.value)} />
              <select aria-label="Event type" className={`${inputCls} max-w-[14rem]`} value={type} onChange={(e) => setType(e.target.value)}>
                <option value="">All types</option>
                {types.map((t) => <option key={t}>{t}</option>)}
              </select>
              <Btn variant="secondary" onClick={() => setOrder((o) => (o === "asc" ? "desc" : "asc"))}>{order === "asc" ? "Oldest first" : "Newest first"}</Btn>
            </div>
            <div className="scroll-x">
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wider text-muted">
                    {["#", "Original timestamp", "UTC", "Timezone", "Type", "Artifact", "Evidence file", "Description"].map((h) => <th key={h} className="border-b border-line px-3 py-2 font-semibold">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {shown.map((e, i) => (
                    <tr key={e.id} className="align-top">
                      <td className="border-b border-line px-3 py-2.5 text-muted">{i + 1}</td>
                      <td className="border-b border-line px-3 py-2.5 font-mono text-xs">{e.event_time_original || "—"}</td>
                      <td className="border-b border-line px-3 py-2.5 font-mono text-xs">{fmtUtc(e.event_time_utc)}</td>
                      <td className="border-b border-line px-3 py-2.5"><StatusBadge value={e.timezone_status} />{e.flag && <p className="mt-1 max-w-[12rem] text-xs text-muted">{e.flag}</p>}</td>
                      <td className="border-b border-line px-3 py-2.5">{e.event_type}</td>
                      <td className="border-b border-line px-3 py-2.5 font-mono text-xs">{e.artifact_reference}</td>
                      <td className="border-b border-line px-3 py-2.5 text-xs text-muted [overflow-wrap:anywhere]">{e.evidence_filename}</td>
                      <td className="border-b border-line px-3 py-2.5 [overflow-wrap:anywhere]">{e.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {shown.length === 0 && <p className="py-6 text-muted">No events match.</p>}
          </Card>
        </>
      )}
    </>
  );
}
