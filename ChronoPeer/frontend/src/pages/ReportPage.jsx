import { useState } from "react";
import { api, downloadBlob } from "../services/api";
import { Btn, Card, Loading, NeedRole, NoCase, Notice, PageTitle, useApp, useLoad } from "../components/ui";

const SECTIONS = [
  ["Investigation details", "Case ID, title, description, date, status."],
  ["Dataset information", "The dataset and the state of its timestamps."],
  ["Evidence inventory", "Every file with its SHA-256, re-checked when the report is built."],
  ["Original timeline", "Every event in chronological order, with original and UTC times."],
  ["Original inferences", "Each conclusion as first recorded, with its supporting events."],
  ["Peer critiques", "Every review disposition and its justification."],
  ["Alternative explanations", "What each reviewer proposed, and the evidence they asked for."],
  ["Revised timeline", "The same events annotated with the current inferences and their status."],
  ["Revision history", "Every response, status change and reason."],
  ["Limitations", "What the method and the data cannot show."],
  ["Final conclusion", "Your conclusion and the outcome of every inference."],
];

export default function ReportPage() {
  const { caseId, currentCase } = useApp();
  const summary = useLoad(() => (caseId ? api.summary(caseId) : Promise.resolve(null)), [caseId]);
  const [state, setState] = useState({ busy: false, error: null, ok: false });

  const generate = async () => {
    setState({ busy: true, error: null, ok: false });
    try {
      downloadBlob(await api.report(caseId), `chronopeer-case-${caseId}-report.pdf`);
      setState({ busy: false, error: null, ok: true });
    } catch (e) {
      setState({ busy: false, error: e.message, ok: false });
    }
  };

  if (!caseId) return <><PageTitle eyebrow="Report" title="Final report" /><NoCase /></>;
  const s = summary.data;
  return (
    <>
      <PageTitle eyebrow="Report" title="Final investigation report" lede="One PDF that lets another examiner follow every conclusion back to the evidence, the challenge and the revision." />
      <Loading error={summary.error} loading={summary.loading && !s} />
      {s && (
        <Card className="mb-8">
          <p className="text-lg font-semibold">{currentCase?.title}</p>
          <p className="mt-2 text-muted">
            {s.timeline.total} events · {s.inferences.total} inferences · {s.pending_reviews} awaiting review · {s.open_challenges} open challenge(s)
          </p>
          {(s.pending_reviews > 0 || s.open_challenges > 0) && (
            <div className="mt-4"><Notice kind="warn">Some inferences are still awaiting review or have unanswered challenges. The report will say so.</Notice></div>
          )}
          <div className="mt-6">
            <NeedRole role="investigator">
              <Btn onClick={generate} disabled={state.busy}>{state.busy ? "Building PDF…" : "Generate PDF report"}</Btn>
            </NeedRole>
          </div>
          {state.error && <div className="mt-4"><Notice kind="bad">{state.error}</Notice></div>}
          {state.ok && <div className="mt-4"><Notice kind="ok">Report downloaded.</Notice></div>}
        </Card>
      )}
      <h2 className="mb-4 text-2xl font-semibold tracking-tight">What the report contains</h2>
      <ol className="grid gap-3 sm:grid-cols-2">
        {SECTIONS.map(([title, text], i) => (
          <li key={title} className="rounded-2xl border border-line bg-surface p-4">
            <p className="font-semibold"><span className="mr-2 font-mono text-sm text-accent">{String(i + 1).padStart(2, "0")}</span>{title}</p>
            <p className="mt-1 text-sm text-muted">{text}</p>
          </li>
        ))}
      </ol>
    </>
  );
}
