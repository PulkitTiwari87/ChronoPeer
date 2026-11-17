import { useCallback, useEffect, useMemo, useState } from "react";
import { api, setIdentity } from "./services/api";
import { AppContext, Notice } from "./components/ui";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import CaseDetails from "./pages/CaseDetails";
import EvidenceUpload from "./pages/EvidenceUpload";
import TimelinePage from "./pages/TimelinePage";
import InferencesPage from "./pages/InferencesPage";
import PeerReviewPage from "./pages/PeerReviewPage";
import RevisionsPage from "./pages/RevisionsPage";
import ReportPage from "./pages/ReportPage";

const ROUTES = {
  "/": Dashboard,
  "/case": CaseDetails,
  "/evidence": EvidenceUpload,
  "/timeline": TimelinePage,
  "/inferences": InferencesPage,
  "/review": PeerReviewPage,
  "/revisions": RevisionsPage,
  "/report": ReportPage,
};

const read = (key, fallback) => {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
};
const write = (key, value) => {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable (private mode): the choice simply is not remembered */
  }
};

function useHashRoute() {
  const current = () => window.location.hash.replace(/^#/, "") || "/";
  const [route, setRoute] = useState(current);
  useEffect(() => {
    const onChange = () => {
      setRoute(current());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export default function App() {
  const route = useHashRoute();
  const [role, setRoleState] = useState(() => (read("cp.role", "investigator") === "reviewer" ? "reviewer" : "investigator"));
  const [names, setNames] = useState(() => ({
    investigator: read("cp.name.investigator", "Investigator"),
    reviewer: read("cp.name.reviewer", "Reviewer"),
  }));
  const [cases, setCases] = useState([]);
  const [caseId, setCaseIdState] = useState(() => Number(read("cp.case", "0")) || null);
  const [error, setError] = useState(null);
  const [ephemeral, setEphemeral] = useState(false);
  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((h) => setEphemeral(Boolean(h.ephemeral)))
      .catch(() => {});
  }, []);

  const actorName = names[role];
  setIdentity(role, actorName); // idempotent; set during render so child effects send the right headers

  const setRole = useCallback((r) => {
    setRoleState(r);
    write("cp.role", r);
  }, []);
  const setActorName = useCallback(
    (name) => {
      setNames((n) => ({ ...n, [role]: name }));
      write(`cp.name.${role}`, name);
    },
    [role],
  );
  const setCaseId = useCallback((id) => {
    setCaseIdState(id || null);
    write("cp.case", String(id || 0));
  }, []);

  const reloadCases = useCallback(async () => {
    try {
      const list = await api.cases();
      setCases(list);
      setError(null);
      setCaseIdState((current) => (list.some((c) => c.id === current) ? current : list[0]?.id || null));
    } catch (e) {
      setError(e.message);
    }
  }, []);
  useEffect(() => {
    reloadCases();
  }, [reloadCases]);

  const value = useMemo(
    () => ({ role, setRole, actorName, setActorName, cases, reloadCases, caseId, setCaseId, currentCase: cases.find((c) => c.id === caseId) || null }),
    [role, setRole, actorName, setActorName, cases, reloadCases, caseId, setCaseId],
  );

  const Page = ROUTES[route] || Dashboard;
  return (
    <AppContext.Provider value={value}>
      <Navbar route={ROUTES[route] ? route : "/"} />
      <main className="mx-auto max-w-6xl px-5 pb-24">
        {ephemeral && (
          <div className="mt-6">
            <Notice kind="warn">
              Hosted demo on temporary storage. Anything you add can disappear when the free server restarts or goes idle; the demo case is always reloaded. For real work, run ChronoPeer locally.
            </Notice>
          </div>
        )}
        {error && (
          <div className="mt-6">
            <Notice kind="bad">Could not reach the ChronoPeer API: {error}</Notice>
          </div>
        )}
        <Page />
      </main>
      <footer className="border-t border-line bg-canvas px-5 py-8 text-xs text-muted">
        <p className="mx-auto max-w-6xl">
          Original evidence is never modified. A matching SHA-256 shows a stored file equals its recorded digest; it does not prove the evidence was authentic or that custody was unbroken.
        </p>
      </footer>
    </AppContext.Provider>
  );
}
