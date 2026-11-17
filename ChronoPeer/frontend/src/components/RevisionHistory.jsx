import StatusBadge from "./StatusBadge";
import { dots } from "./ui";

const when = (iso) => iso.replace("T", " ").replace("Z", " UTC");

function Step({ title, meta, children }) {
  return (
    <li className="relative">
      <span className="absolute -left-[31px] top-1.5 h-3 w-3 rounded-full border-2 border-page bg-accent" aria-hidden="true" />
      <p className="text-sm font-semibold">{title}</p>
      <p className="text-xs text-muted">{meta}</p>
      <div className="mt-1 text-sm leading-relaxed">{children}</div>
    </li>
  );
}

/** Original conclusion, then every peer review and investigator response in order, then the current state. */
export default function RevisionHistory({ history }) {
  return (
    <ol className="ml-3 space-y-6 border-l border-line pl-6">
      <Step title="Original conclusion" meta={when(history.original.created_at)}>
        <p>{history.original.explanation}</p>
        <p className="text-muted">Confidence {dots(history.original.confidence)}</p>
      </Step>
      {history.steps.map((s) =>
        s.kind === "review" ? (
          <Step key={`r${s.id}`} title={`Peer review: ${s.reviewer_name}`} meta={`${when(s.created_at)} · round ${s.round}`}>
            <p className="mb-1"><StatusBadge value={s.decision} /></p>
            <p>{s.critique}</p>
            {s.alternative_explanation && <p className="mt-1 text-muted"><strong>Alternative:</strong> {s.alternative_explanation}</p>}
            {s.additional_evidence && <p className="mt-1 text-muted"><strong>Evidence requested:</strong> {s.additional_evidence}</p>}
          </Step>
        ) : (
          <Step key={`v${s.id}`} title={`Investigator response: ${s.response.replace(/_/g, " ")}`} meta={`${when(s.created_at)} · ${s.actor_name}`}>
            <p className="mb-1 flex items-center gap-2"><StatusBadge value={s.previous_status} /> → <StatusBadge value={s.new_status} /></p>
            <p>{s.change_reason}</p>
            {s.previous_explanation !== s.revised_explanation && (
              <p className="mt-1 text-muted"><strong>Now reads:</strong> {s.revised_explanation}</p>
            )}
          </Step>
        ),
      )}
      <Step title="Current conclusion" meta={`status ${history.current.status}`}>
        <p>{history.current.explanation}</p>
        <p className="text-muted">Confidence {dots(history.current.confidence)}</p>
      </Step>
    </ol>
  );
}
