import { useState } from "react";
import { api } from "../services/api";
import StatusBadge from "./StatusBadge";
import { Btn, Field, Notice, inputCls } from "./ui";

const RESPONSES = [
  ["accepted", "Accept the challenge"],
  ["partially_accepted", "Partially accept"],
  ["rejected", "Reject (needs justification)"],
  ["modified", "Modify the inference"],
  ["unresolved", "Mark unresolved"],
];
const STATUSES = ["", "proposed", "challenged", "agreed", "revised", "retained", "unresolved", "withdrawn"];

/** Investigator response to the open peer reviews of one inference. `history` comes from /inferences/{id}/history. */
export default function ReviewPanel({ inf, history, onDone }) {
  const answered = new Set(history.steps.filter((s) => s.kind === "revision" && s.peer_review_id).map((s) => s.peer_review_id));
  const open = history.steps.filter((s) => s.kind === "review" && !answered.has(s.id));
  const [reviewId, setReviewId] = useState(open[0]?.id || "");
  const [response, setResponse] = useState("accepted");
  const [explanation, setExplanation] = useState(inf.explanation);
  const [reasoning, setReasoning] = useState(inf.reasoning);
  const [confidence, setConfidence] = useState(inf.confidence);
  const [newStatus, setNewStatus] = useState("");
  const [reason, setReason] = useState("");
  const [state, setState] = useState({ busy: false, error: null });

  const submit = async (e) => {
    e.preventDefault();
    setState({ busy: true, error: null });
    try {
      const json = { response, change_reason: reason, peer_review_id: reviewId ? Number(reviewId) : null };
      if (response !== "rejected") {
        json.revised_explanation = explanation;
        json.revised_reasoning = reasoning;
        json.new_confidence = Number(confidence);
      }
      if (newStatus) json.new_status = newStatus;
      await api.respond(inf.id, json);
      setState({ busy: false, error: null });
      onDone();
    } catch (err) {
      setState({ busy: false, error: err.message });
    }
  };

  return (
    <div className="mt-5 space-y-5 border-t border-line pt-5">
      {open.map((r) => (
        <div key={r.id} className="rounded-2xl bg-canvas p-4 text-sm">
          <p className="mb-1 flex items-center gap-2 font-semibold">{r.reviewer_name} <StatusBadge value={r.decision} /></p>
          <p>{r.critique}</p>
          {r.alternative_explanation && <p className="mt-2 text-muted"><strong>Alternative:</strong> {r.alternative_explanation}</p>}
          {r.additional_evidence && <p className="mt-1 text-muted"><strong>Evidence requested:</strong> {r.additional_evidence}</p>}
        </div>
      ))}
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="Responding to">
          <select className={inputCls} value={reviewId} onChange={(e) => setReviewId(e.target.value)}>
            <option value="">No specific review</option>
            {open.map((r) => <option key={r.id} value={r.id}>{r.reviewer_name} ({r.decision})</option>)}
          </select>
        </Field>
        <Field label="Your response">
          <select className={inputCls} value={response} onChange={(e) => setResponse(e.target.value)}>
            {RESPONSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </Field>
        {response !== "rejected" && (
          <>
            <div className="sm:col-span-2">
              <Field label="Revised explanation"><textarea rows={2} className={inputCls} value={explanation} onChange={(e) => setExplanation(e.target.value)} /></Field>
            </div>
            <div className="sm:col-span-2">
              <Field label="Revised reasoning" hint="The original reasoning stays on record."><textarea rows={4} className={inputCls} value={reasoning} onChange={(e) => setReasoning(e.target.value)} /></Field>
            </div>
            <Field label="Confidence (1–5)">
              <select className={inputCls} value={confidence} onChange={(e) => setConfidence(e.target.value)}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select>
            </Field>
          </>
        )}
        <Field label="New status" hint="Leave blank for the default for this response.">
          <select className={inputCls} value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
            {STATUSES.map((s) => <option key={s} value={s}>{s || "Default"}</option>)}
          </select>
        </Field>
        <div className="sm:col-span-2">
          <Field label="Justification (required)"><textarea rows={2} className={inputCls} value={reason} onChange={(e) => setReason(e.target.value)} required /></Field>
        </div>
        {state.error && <div className="sm:col-span-2"><Notice kind="bad">{state.error}</Notice></div>}
        <div className="sm:col-span-2"><Btn type="submit" onClick={undefined} disabled={state.busy || !reason.trim()}>Record response</Btn></div>
      </form>
    </div>
  );
}
