import { useState } from "react";
import { api } from "../services/api";
import { Btn, Card, Field, Loading, NeedRole, Notice, PageTitle, inputCls, useApp, useLoad } from "../components/ui";

const STATUSES = ["open", "under review", "closed"];

function CaseForm({ initial, onSaved }) {
  const editing = Boolean(initial);
  const [form, setForm] = useState({
    case_code: "",
    title: "",
    description: "",
    dataset_name: "",
    investigation_date: new Date().toISOString().slice(0, 10),
    status: "open",
    conclusion: "",
    ...(initial || {}),
  });
  const [state, setState] = useState({ busy: false, error: null, saved: false });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setState({ busy: true, error: null, saved: false });
    try {
      const body = { title: form.title, description: form.description, dataset_name: form.dataset_name, investigation_date: form.investigation_date, status: form.status };
      let saved;
      if (editing) saved = await api.updateCase(initial.id, { ...body, conclusion: form.conclusion });
      else saved = await api.createCase({ ...body, case_code: form.case_code || null });
      setState({ busy: false, error: null, saved: true });
      onSaved(saved);
    } catch (err) {
      setState({ busy: false, error: err.message, saved: false });
    }
  };

  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
      {!editing && <Field label="Case ID (optional label)"><input className={inputCls} value={form.case_code} onChange={set("case_code")} maxLength={64} placeholder="e.g. DF-PBL-040" /></Field>}
      <div className={editing ? "sm:col-span-2" : ""}><Field label="Title"><input className={inputCls} value={form.title} onChange={set("title")} required maxLength={200} /></Field></div>
      <div className="sm:col-span-2"><Field label="Description"><textarea rows={3} className={inputCls} value={form.description} onChange={set("description")} /></Field></div>
      <Field label="Dataset information"><input className={inputCls} value={form.dataset_name} onChange={set("dataset_name")} maxLength={200} /></Field>
      <Field label="Investigation date"><input type="date" className={inputCls} value={form.investigation_date} onChange={set("investigation_date")} /></Field>
      <Field label="Status"><select className={inputCls} value={form.status} onChange={set("status")}>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select></Field>
      {editing && <div className="sm:col-span-2"><Field label="Final conclusion" hint="Printed in section 11 of the report."><textarea rows={4} className={inputCls} value={form.conclusion} onChange={set("conclusion")} /></Field></div>}
      {state.error && <div className="sm:col-span-2"><Notice kind="bad">{state.error}</Notice></div>}
      {state.saved && <div className="sm:col-span-2"><Notice kind="ok">Saved.</Notice></div>}
      <div className="sm:col-span-2"><Btn type="submit" disabled={state.busy || !form.title.trim()}>{editing ? "Save changes" : "Create investigation"}</Btn></div>
    </form>
  );
}

export default function CaseDetails() {
  const { currentCase, caseId, reloadCases, setCaseId } = useApp();
  const [creating, setCreating] = useState(!currentCase);
  const summary = useLoad(() => (caseId ? api.summary(caseId) : Promise.resolve(null)), [caseId, currentCase?.status]);
  return (
    <>
      <PageTitle eyebrow="Case" title="Investigation details" lede="The case record: what is being investigated, with which dataset, and how it ends." />
      {summary.data && (
        <Card className="mb-8">
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-5">
            {[
              ["Evidence files", summary.data.evidence_files],
              ["Events", summary.data.timeline.total],
              ["Inferences", summary.data.inferences.total],
              ["Awaiting review", summary.data.pending_reviews],
              ["Open challenges", summary.data.open_challenges],
            ].map(([k, v]) => (
              <div key={k}><dt className="text-muted">{k}</dt><dd className="display text-3xl font-semibold">{v}</dd></div>
            ))}
          </dl>
        </Card>
      )}
      <Loading error={summary.error} loading={false} />
      <NeedRole role="investigator">
        <Card>
          <div className="mb-5 flex items-center justify-between gap-3">
            <h2 className="text-2xl font-semibold tracking-tight">{creating || !currentCase ? "New investigation" : "Edit investigation"}</h2>
            {currentCase && <Btn variant="ghost" onClick={() => setCreating((c) => !c)}>{creating ? "Edit current case" : "New investigation"}</Btn>}
          </div>
          {creating || !currentCase ? (
            <CaseForm key="new" onSaved={async (saved) => { await reloadCases(); setCaseId(saved.id); setCreating(false); }} />
          ) : (
            <CaseForm key={currentCase.id} initial={currentCase} onSaved={reloadCases} />
          )}
        </Card>
      </NeedRole>
    </>
  );
}
