import { useState } from "react";
import { api } from "../services/api";
import InferenceCard from "../components/InferenceCard";
import { Btn, Card, Field, Loading, NeedRole, NoCase, Notice, PageTitle, inputCls, useApp, useLoad } from "../components/ui";

function NewInference({ caseId, onCreated }) {
  const events = useLoad(() => api.timeline(caseId), [caseId]);
  const [form, setForm] = useState({ title: "", explanation: "", reasoning: "", confidence: 3 });
  const [picked, setPicked] = useState(new Set());
  const [filter, setFilter] = useState("");
  const [state, setState] = useState({ busy: false, error: null });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const toggle = (id) => setPicked((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const list = (events.data?.events || []).filter((e) => `${e.description} ${e.artifact_reference}`.toLowerCase().includes(filter.toLowerCase()));

  const submit = async (e) => {
    e.preventDefault();
    setState({ busy: true, error: null });
    try {
      await api.createInference(caseId, { ...form, confidence: Number(form.confidence), event_ids: [...picked] });
      setForm({ title: "", explanation: "", reasoning: "", confidence: 3 });
      setPicked(new Set());
      setState({ busy: false, error: null });
      onCreated();
    } catch (err) {
      setState({ busy: false, error: err.message });
    }
  };

  return (
    <form onSubmit={submit} className="grid gap-4">
      <Field label="Title"><input className={inputCls} value={form.title} onChange={set("title")} required maxLength={300} /></Field>
      <Field label="Explanation" hint="What you conclude happened."><textarea rows={2} className={inputCls} value={form.explanation} onChange={set("explanation")} required /></Field>
      <Field label="Reasoning" hint="Why the evidence supports it."><textarea rows={3} className={inputCls} value={form.reasoning} onChange={set("reasoning")} required /></Field>
      <div className="max-w-[10rem]"><Field label="Confidence (1–5)"><select className={inputCls} value={form.confidence} onChange={set("confidence")}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select></Field></div>
      <fieldset>
        <legend className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted">Supporting events ({picked.size} selected, at least one required)</legend>
        <input aria-label="Filter events" className={`${inputCls} mb-2`} placeholder="Filter events" value={filter} onChange={(e) => setFilter(e.target.value)} />
        <div className="max-h-64 space-y-1 overflow-y-auto rounded-2xl border border-line p-2">
          {list.map((e) => (
            <label key={e.id} className="flex cursor-pointer items-start gap-3 rounded-xl px-2 py-1.5 text-sm hover:bg-canvas">
              <input type="checkbox" className="mt-1" checked={picked.has(e.id)} onChange={() => toggle(e.id)} />
              <span><strong className="font-mono text-xs">{e.artifact_reference}</strong> <span className="text-muted">{e.event_time_original}</span><br />{e.description}</span>
            </label>
          ))}
          {list.length === 0 && <p className="p-2 text-sm text-muted">No events.</p>}
        </div>
      </fieldset>
      {state.error && <Notice kind="bad">{state.error}</Notice>}
      <div><Btn type="submit" disabled={state.busy || picked.size === 0}>Create inference</Btn></div>
    </form>
  );
}

export default function InferencesPage() {
  const { caseId } = useApp();
  const { data, error, loading, reload } = useLoad(() => (caseId ? api.inferences(caseId) : Promise.resolve([])), [caseId]);
  const [adding, setAdding] = useState(false);
  if (!caseId) return <><PageTitle eyebrow="Inferences" title="Inferences" /><NoCase /></>;
  return (
    <>
      <PageTitle
        eyebrow="Inferences"
        title="What the evidence supports"
        lede="Each inference cites the events it rests on, states a confidence, and goes to a reviewer for an explicit disposition."
      />
      <NeedRole role="investigator">
        <Card className="mb-8">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-2xl font-semibold tracking-tight">New inference</h2>
            <Btn variant="secondary" onClick={() => setAdding((a) => !a)}>{adding ? "Close" : "Add inference"}</Btn>
          </div>
          {adding && <div className="mt-5"><NewInference caseId={caseId} onCreated={() => { reload(); setAdding(false); }} /></div>}
        </Card>
      </NeedRole>
      <Loading error={error} loading={loading && !data} />
      <div className="space-y-5">
        {data?.map((inf) => <InferenceCard key={inf.id} inf={inf} />)}
        {data?.length === 0 && <p className="text-muted">No inferences yet.</p>}
      </div>
    </>
  );
}
