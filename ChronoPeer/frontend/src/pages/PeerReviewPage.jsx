import { useState } from "react";
import { api } from "../services/api";
import InferenceCard from "../components/InferenceCard";
import StatusBadge from "../components/StatusBadge";
import { Btn, Card, Chip, Field, Loading, NeedRole, NoCase, Notice, PageTitle, inputCls, useApp, useLoad } from "../components/ui";

function ReviewForm({ inf, onDone }) {
  const { actorName } = useApp();
  const [decision, setDecision] = useState("challenge");
  const [f, setF] = useState({ critique: "", alternative_explanation: "", additional_evidence: "", confidence: 3 });
  const [state, setState] = useState({ busy: false, error: null, ok: false });
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const challenge = decision === "challenge";

  const submit = async (e) => {
    e.preventDefault();
    setState({ busy: true, error: null, ok: false });
    try {
      await api.submitReview(inf.id, { reviewer_name: actorName, decision, ...f, confidence: Number(f.confidence), alternative_explanation: challenge ? f.alternative_explanation : f.alternative_explanation || "" });
      setF({ critique: "", alternative_explanation: "", additional_evidence: "", confidence: 3 });
      setState({ busy: false, error: null, ok: true });
      onDone();
    } catch (err) {
      setState({ busy: false, error: err.message, ok: false });
    }
  };

  return (
    <form onSubmit={submit} className="mt-6 grid gap-4 border-t border-line pt-6">
      <p className="text-sm text-muted">Reviewing as <strong className="text-ink">{actorName}</strong> (round {inf.review_state.round}). Every inference needs an explicit disposition, with a justification either way.</p>
      <div role="radiogroup" aria-label="Disposition" className="flex gap-2">
        {[["agree", "Agree"], ["challenge", "Challenge"]].map(([v, l]) => (
          <button key={v} type="button" role="radio" aria-checked={decision === v} onClick={() => setDecision(v)}
            className={`rounded-full px-5 py-2 text-sm font-medium ${decision === v ? "bg-accent text-white" : "bg-neutral-bg"}`}>{l}</button>
        ))}
      </div>
      <Field label={challenge ? "Why the conclusion may be unsupported" : "Why you agree"}><textarea rows={3} className={inputCls} value={f.critique} onChange={set("critique")} required /></Field>
      <Field label="Alternative explanation" hint={challenge ? "Required for a challenge." : "Optional."}><textarea rows={3} className={inputCls} value={f.alternative_explanation} onChange={set("alternative_explanation")} required={challenge} /></Field>
      <Field label="Additional evidence needed"><textarea rows={2} className={inputCls} value={f.additional_evidence} onChange={set("additional_evidence")} /></Field>
      <div className="max-w-[10rem]"><Field label="Your confidence (1–5)"><select className={inputCls} value={f.confidence} onChange={set("confidence")}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select></Field></div>
      {state.error && <Notice kind="bad">{state.error}</Notice>}
      {state.ok && <Notice kind="ok">Review recorded.</Notice>}
      <div><Btn type="submit" disabled={state.busy || !f.critique.trim()}>Submit review</Btn></div>
    </form>
  );
}

export default function PeerReviewPage() {
  const { caseId } = useApp();
  const inferences = useLoad(() => (caseId ? api.inferences(caseId) : Promise.resolve([])), [caseId]);
  const [selected, setSelected] = useState(null);
  const current = inferences.data?.find((i) => i.id === selected) || inferences.data?.[0] || null;
  const reviews = useLoad(() => (current ? api.reviews(current.id) : Promise.resolve([])), [current?.id, current?.review_state.reviews_total]);

  if (!caseId) return <><PageTitle eyebrow="Peer review" title="Peer review" /><NoCase /></>;
  return (
    <>
      <PageTitle
        eyebrow="Peer review"
        title="Challenge every inference"
        lede="Read the original conclusion and its supporting events, then agree or challenge it. A challenge must offer an alternative explanation."
      />
      <NeedRole role="reviewer">
        <Loading error={inferences.error} loading={inferences.loading && !inferences.data} />
        {inferences.data && (
          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            <nav aria-label="Inferences to review" className="space-y-2">
              {inferences.data.map((i) => (
                <button key={i.id} type="button" onClick={() => setSelected(i.id)}
                  className={`w-full rounded-2xl border p-4 text-left text-sm ${current?.id === i.id ? "border-accent bg-surface" : "border-line bg-surface"}`}>
                  <span className="flex items-start justify-between gap-2"><span className="font-semibold">{i.title}</span></span>
                  <span className="mt-2 flex flex-wrap items-center gap-2"><StatusBadge value={i.status} />{i.review_state.pending_review && <Chip kind="warn">awaiting</Chip>}</span>
                </button>
              ))}
            </nav>
            {current && (
              <div>
                <InferenceCard inf={current}>
                  {reviews.data?.length > 0 && (
                    <div className="mt-5 space-y-3 border-t border-line pt-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-muted">Reviews so far</p>
                      {reviews.data.map((r) => (
                        <div key={r.id} className="rounded-2xl bg-canvas p-3 text-sm">
                          <p className="flex items-center gap-2 font-semibold">{r.reviewer_name} <StatusBadge value={r.decision} /> <span className="font-normal text-muted">round {r.round}</span></p>
                          <p className="mt-1">{r.critique}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  <ReviewForm key={`${current.id}-${current.review_state.round}`} inf={current} onDone={() => { inferences.reload(); reviews.reload(); }} />
                </InferenceCard>
              </div>
            )}
          </div>
        )}
      </NeedRole>
    </>
  );
}
