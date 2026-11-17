import { useState } from "react";
import { api } from "../services/api";
import InferenceCard from "../components/InferenceCard";
import ReviewPanel from "../components/ReviewPanel";
import RevisionHistory from "../components/RevisionHistory";
import { Card, Loading, NeedRole, NoCase, PageTitle, useApp, useLoad } from "../components/ui";

function HistoryBody({ id, version }) {
  const { data, error, loading } = useLoad(() => api.history(id), [id, version]);
  return (
    <div className="mt-4">
      <Loading error={error} loading={loading && !data} />
      {data && <RevisionHistory history={data} />}
    </div>
  );
}

function Respond({ inf, onDone }) {
  const { data, error, loading } = useLoad(() => api.history(inf.id), [inf.id, inf.review_state.reviews_total, inf.status]);
  return (
    <>
      <Loading error={error} loading={loading && !data} />
      {data && <ReviewPanel key={`${inf.id}-${inf.status}-${data.steps.length}`} inf={inf} history={data} onDone={onDone} />}
    </>
  );
}

function Item({ inf, onDone }) {
  const [open, setOpen] = useState(false);
  return (
    <InferenceCard inf={inf}>
      {inf.review_state.open_challenges > 0 && (
        <NeedRole role="investigator">
          <Respond inf={inf} onDone={onDone} />
        </NeedRole>
      )}
      <details className="mt-4 border-t border-line pt-3" onToggle={(e) => setOpen(e.currentTarget.open)}>
        <summary className="cursor-pointer text-sm text-accent">Full revision history</summary>
        {open && <HistoryBody id={inf.id} version={`${inf.status}-${inf.updated_at}`} />}
      </details>
    </InferenceCard>
  );
}

export default function RevisionsPage() {
  const { caseId } = useApp();
  const { data, error, loading, reload } = useLoad(() => (caseId ? api.inferences(caseId) : Promise.resolve([])), [caseId]);
  if (!caseId) return <><PageTitle eyebrow="Revisions" title="Revisions" /><NoCase /></>;
  const waiting = data?.filter((i) => i.review_state.open_challenges > 0) || [];
  return (
    <>
      <PageTitle
        eyebrow="Revisions"
        title="Respond, revise, keep the history"
        lede="Accept, partly accept or reject each challenge with a justification. The original conclusion, the challenge and every revision stay on record."
      />
      <Loading error={error} loading={loading && !data} />
      {data && (
        <>
          <Card className="mb-8">
            <p className="text-lg"><strong>{waiting.length}</strong> inference(s) have an unanswered challenge.</p>
            <p className="mt-1 text-sm text-muted">Open one below to respond (investigator mode).</p>
          </Card>
          <div className="space-y-5">
            {data.map((inf) => <Item key={inf.id} inf={inf} onDone={reload} />)}
          </div>
        </>
      )}
    </>
  );
}
