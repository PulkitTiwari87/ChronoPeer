import { api } from "../services/api";
import { Btn, Card, Loading, PageTitle, useApp, useLoad } from "../components/ui";

export default function Dashboard() {
  const { cases, caseId, setCaseId } = useApp();
  const { data, error, loading } = useLoad(() => api.dashboard(), [cases.length, caseId]);
  const tiles = data && [
    ["Investigations", data.investigations],
    ["Evidence files", data.evidence_files],
    ["Timeline events", data.timeline_events],
    ["Inferences", data.inferences],
    ["Awaiting review", data.pending_reviews],
  ];
  return (
    <>
      <PageTitle
        eyebrow="Forensic incident timelines"
        title="Read the evidence. Challenge every inference."
        lede="Import evidence, build a chronological timeline, record what you infer from it, and have a reviewer propose an alternative for every conclusion. Nothing is overwritten."
      />
      <Loading error={error} loading={loading && !data} />
      {data && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            {tiles.map(([label, n]) => (
              <Card key={label} className="!p-5">
                <p className="display text-4xl font-semibold">{n}</p>
                <p className="mt-1 text-sm text-muted">{label}</p>
              </Card>
            ))}
          </div>
          <div className="mt-10 grid gap-6 lg:grid-cols-2">
            <Card>
              <h2 className="mb-4 text-2xl font-semibold tracking-tight">Investigations</h2>
              {cases.length === 0 && <p className="text-muted">None yet. Create one on the Case page.</p>}
              <ul className="space-y-3">
                {cases.map((c) => (
                  <li key={c.id} className="flex items-start justify-between gap-3 rounded-2xl bg-canvas p-4">
                    <div className="min-w-0">
                      <p className="font-semibold">{c.title}</p>
                      <p className="text-sm text-muted">{c.case_code ? `${c.case_code} · ` : ""}{c.status} · {c.investigation_date}</p>
                    </div>
                    <Btn variant={c.id === caseId ? "secondary" : "primary"} onClick={() => { setCaseId(c.id); window.location.hash = "#/timeline"; }}>
                      {c.id === caseId ? "Open timeline" : "Open"}
                    </Btn>
                  </li>
                ))}
              </ul>
            </Card>
            <Card>
              <h2 className="mb-4 text-2xl font-semibold tracking-tight">Recent activity</h2>
              {data.recent_activity.length === 0 && <p className="text-muted">Nothing recorded yet.</p>}
              <ul className="space-y-3">
                {data.recent_activity.map((a) => (
                  <li key={a.id} className="text-sm">
                    <p>{a.description}</p>
                    <p className="text-xs text-muted">{a.actor_name} ({a.actor_role}) · {a.created_at.replace("T", " ").replace("Z", " UTC")}</p>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
