import { ROLE_LABEL, useApp } from "./ui";

const LINKS = [
  ["/", "Dashboard"],
  ["/case", "Case"],
  ["/evidence", "Evidence"],
  ["/timeline", "Timeline"],
  ["/inferences", "Inferences"],
  ["/review", "Peer review"],
  ["/revisions", "Revisions"],
  ["/report", "Report"],
];

export default function Navbar({ route }) {
  const { role, setRole, actorName, setActorName, cases, caseId, setCaseId } = useApp();
  return (
    <header className="nav-glass sticky top-0 z-20 border-b border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-5 py-2.5">
        <a href="#/" className="text-[17px] font-semibold tracking-tight">ChronoPeer</a>
        <select
          aria-label="Investigation"
          value={caseId || ""}
          onChange={(e) => setCaseId(Number(e.target.value))}
          className="max-w-[16rem] rounded-full border border-line bg-page px-3 py-1.5 text-sm"
        >
          {cases.length === 0 && <option value="">No investigations</option>}
          {cases.map((c) => (
            <option key={c.id} value={c.id}>{c.case_code ? `${c.case_code} · ` : ""}{c.title}</option>
          ))}
        </select>
        <div className="ml-auto flex items-center gap-2">
          <div role="group" aria-label="Operating mode" className="flex rounded-full bg-neutral-bg p-1 text-sm font-medium">
            {["investigator", "reviewer"].map((r) => (
              <button
                key={r}
                type="button"
                aria-pressed={role === r}
                onClick={() => setRole(r)}
                className={`rounded-full px-3.5 py-1 ${role === r ? "bg-page shadow-sm" : "text-muted"}`}
              >
                {ROLE_LABEL[r]}
              </button>
            ))}
          </div>
          <input
            aria-label={`${ROLE_LABEL[role]} name`}
            value={actorName}
            onChange={(e) => setActorName(e.target.value)}
            maxLength={80}
            className="w-32 rounded-full border border-line bg-page px-3 py-1.5 text-sm"
          />
        </div>
      </div>
      <nav aria-label="Pages" className="scroll-x mx-auto flex max-w-6xl gap-1 px-4 pb-2">
        {LINKS.map(([path, label]) => (
          <a
            key={path}
            href={`#${path}`}
            aria-current={route === path ? "page" : undefined}
            className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-sm ${route === path ? "bg-neutral-bg font-semibold text-ink" : "text-muted hover:text-ink"}`}
          >
            {label}
          </a>
        ))}
      </nav>
      <p className="mx-auto max-w-6xl px-5 pb-2 text-xs text-muted">
        Current mode: <strong className="text-ink">{ROLE_LABEL[role]}</strong> as “{actorName}”. Modes separate duties; they are not authentication.
      </p>
    </header>
  );
}
