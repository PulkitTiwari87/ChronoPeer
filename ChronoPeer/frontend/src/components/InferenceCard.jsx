import StatusBadge from "./StatusBadge";
import { Card, Chip, dots } from "./ui";

export default function InferenceCard({ inf, children }) {
  const changed =
    inf.reasoning !== inf.original_reasoning || inf.explanation !== inf.original_explanation || inf.confidence !== inf.original_confidence;
  const rs = inf.review_state;
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h3 className="text-xl font-semibold tracking-tight">{inf.title}</h3>
        <StatusBadge value={inf.status} />
      </div>
      <p className="mt-3 text-[15px] leading-relaxed">{inf.explanation}</p>
      <p className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
        <span>
          Confidence <span className="font-mono text-ink" title={`${inf.confidence} of 5`}>{dots(inf.confidence)}</span>
        </span>
        <span>{rs.reviews_total} review(s)</span>
        <span>{rs.open_challenges} open challenge(s)</span>
        {rs.pending_review && <Chip kind="warn">awaiting review · round {rs.round}</Chip>}
      </p>
      <div className="mt-3 flex flex-wrap gap-2" aria-label="Supporting events">
        {inf.events.map((e) => (
          <Chip key={e.id} title={e.description}>{e.artifact_reference}</Chip>
        ))}
      </div>
      <details className="mt-4 border-t border-line pt-3">
        <summary className="cursor-pointer text-sm text-accent">Reasoning{changed ? " (revised, original preserved)" : ""}</summary>
        <p className="mt-3 whitespace-pre-line text-sm leading-relaxed">{inf.reasoning}</p>
        {changed && (
          <div className="mt-4 rounded-2xl bg-canvas p-4 text-sm">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted">Original conclusion (never overwritten)</p>
            <p>{inf.original_explanation}</p>
            <p className="mt-2 whitespace-pre-line text-muted">{inf.original_reasoning}</p>
            <p className="mt-2 text-muted">Original confidence {inf.original_confidence} / 5</p>
          </div>
        )}
      </details>
      {children}
    </Card>
  );
}
