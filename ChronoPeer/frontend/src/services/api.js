// Thin fetch wrapper. Every request carries the current operating role (X-Role) and actor name (X-Actor).
// There is no authentication: the role separates the two modes, it does not prove who is calling.
const identity = { role: "investigator", actor: "Investigator" };

export function setIdentity(role, actor) {
  identity.role = role;
  identity.actor = (actor || "").replace(/[^\x20-\x7e]/g, "").trim().slice(0, 80) || role;
}

async function errorText(res) {
  try {
    const data = await res.json();
    const d = data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`).join("; ");
  } catch {
    /* body was not JSON */
  }
  return `${res.status} ${res.statusText}`;
}

async function request(path, { method = "GET", json, form } = {}) {
  const headers = { "X-Role": identity.role, "X-Actor": identity.actor };
  let body;
  if (form) body = form;
  else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }
  const res = await fetch(`/api${path}`, { method, headers, body });
  if (!res.ok) throw new Error(await errorText(res));
  return (res.headers.get("content-type") || "").includes("application/pdf") ? res.blob() : res.json();
}

function formOf(file, tz) {
  const f = new FormData();
  f.append("file", file);
  f.append("assume_timezone", tz || "");
  return f;
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const api = {
  dashboard: () => request("/dashboard"),
  cases: () => request("/cases"),
  createCase: (json) => request("/cases", { method: "POST", json }),
  updateCase: (id, json) => request(`/cases/${id}`, { method: "PATCH", json }),
  summary: (id) => request(`/cases/${id}/summary`),
  audit: (id) => request(`/cases/${id}/audit`),
  evidence: (id) => request(`/cases/${id}/evidence`),
  previewEvidence: (id, file, tz) => request(`/cases/${id}/evidence/preview`, { method: "POST", form: formOf(file, tz) }),
  importEvidence: (id, file, tz) => request(`/cases/${id}/evidence`, { method: "POST", form: formOf(file, tz) }),
  verifyEvidence: (id) => request(`/evidence/${id}/verify`),
  timeline: (id, order = "asc") => request(`/cases/${id}/timeline?order=${order}`),
  inferences: (id) => request(`/cases/${id}/inferences`),
  createInference: (id, json) => request(`/cases/${id}/inferences`, { method: "POST", json }),
  history: (inferenceId) => request(`/inferences/${inferenceId}/history`),
  reviews: (inferenceId) => request(`/inferences/${inferenceId}/reviews`),
  submitReview: (inferenceId, json) => request(`/inferences/${inferenceId}/reviews`, { method: "POST", json }),
  respond: (inferenceId, json) => request(`/inferences/${inferenceId}/revisions`, { method: "POST", json }),
  caseRevisions: (id) => request(`/cases/${id}/revisions`),
  report: (id) => request(`/cases/${id}/report`),
};
