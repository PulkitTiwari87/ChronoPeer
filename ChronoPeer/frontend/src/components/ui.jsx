import { createContext, useContext, useEffect, useState } from "react";

export const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);

export const ROLE_LABEL = { investigator: "Investigator", reviewer: "Peer reviewer" };

/** Run an async loader; returns {data, error, loading, reload}. */
export function useLoad(fn, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true }));
    fn()
      .then((data) => alive && setState({ data, error: null, loading: false }))
      .catch((e) => alive && setState({ data: null, error: e.message, loading: false }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, reload: () => setTick((t) => t + 1) };
}

export const inputCls =
  "w-full rounded-xl border border-line bg-page px-3.5 py-2.5 text-[15px] text-ink placeholder:text-muted focus:border-accent";

export function Card({ className = "", children }) {
  return <section className={`rounded-3xl border border-line bg-surface p-5 sm:p-7 ${className}`}>{children}</section>;
}

export function PageTitle({ eyebrow, title, lede, children }) {
  return (
    <header className="mb-8 mt-10 sm:mb-10 sm:mt-14">
      {eyebrow && <p className="mb-3 text-xs font-semibold uppercase tracking-[0.1em] text-muted">{eyebrow}</p>}
      <h1 className="display text-4xl font-semibold sm:text-5xl">{title}</h1>
      {lede && <p className="mt-4 max-w-2xl text-lg leading-snug text-muted">{lede}</p>}
      {children}
    </header>
  );
}

export function Btn({ variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-accent text-white hover:bg-accent-hi",
    secondary: "bg-neutral-bg text-ink hover:bg-line",
    ghost: "text-accent hover:underline px-1",
    danger: "bg-bad-bg text-bad",
  }[variant];
  return (
    <button type="button" {...props} className={`rounded-full px-5 py-2.5 text-[15px] font-medium disabled:opacity-40 ${styles} ${className}`} />
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function Notice({ kind = "info", children }) {
  const tone = { info: "bg-neutral-bg text-ink", ok: "bg-ok-bg text-ok", warn: "bg-warn-bg text-warn", bad: "bg-bad-bg text-bad" }[kind];
  return (
    <div role={kind === "bad" ? "alert" : "status"} className={`rounded-2xl px-4 py-3 text-sm ${tone}`}>
      {children}
    </div>
  );
}

export function Chip({ kind = "neutral", children, title }) {
  const tone = {
    neutral: "bg-neutral-bg text-muted",
    ok: "bg-ok-bg text-ok",
    warn: "bg-warn-bg text-warn",
    bad: "bg-bad-bg text-bad",
    accent: "bg-accent/15 text-accent",
  }[kind];
  return (
    <span title={title} className={`inline-block max-w-full rounded-full px-3 py-1 text-xs font-semibold ${tone}`}>
      {children}
    </span>
  );
}

export function Loading({ error, loading }) {
  if (error) return <Notice kind="bad">{error}</Notice>;
  if (loading) return <p className="py-6 text-muted">Loading…</p>;
  return null;
}

/** Shows children only in the right operating mode; otherwise offers a one-click switch. */
export function NeedRole({ role, children }) {
  const { role: current, setRole } = useApp();
  if (current === role) return children;
  return (
    <Notice kind="warn">
      This action belongs to {ROLE_LABEL[role]} mode, and you are in {ROLE_LABEL[current]} mode.
      <button type="button" className="ml-2 font-semibold underline" onClick={() => setRole(role)}>
        Switch to {ROLE_LABEL[role]} mode
      </button>
    </Notice>
  );
}

export function NoCase() {
  return (
    <Card>
      <p className="text-lg">No investigation is selected.</p>
      <p className="mt-2 text-muted">
        Create one on the <a className="text-accent hover:underline" href="#/case">Case</a> page.
      </p>
    </Card>
  );
}

export const fmtUtc = (iso) => (iso ? iso.replace("T", " ").replace("Z", " UTC") : "—");
export const dots = (n) => "●".repeat(n) + "○".repeat(5 - n);
