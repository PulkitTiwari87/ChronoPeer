#!/usr/bin/env python3
"""Live end-to-end test of a deployed ChronoPeer, with a step-by-step record.

Usage:  python demo/live_test.py [base_url]       (default https://chronopeer.vercel.app)
Needs:  httpx (the project venv has it)
It creates ONE clearly labelled test investigation; the bundled demo case is only read.
Writes demo/output/live_test_report.md and live_test_results.json. Exit code 0 only if every step passed.
"""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://chronopeer.vercel.app").rstrip("/")
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
SAMPLE = HERE / "sample_evidence.csv"
INV = {"X-Role": "investigator", "X-Actor": "Live tester"}
REV = {"X-Role": "reviewer", "X-Actor": "Live reviewer"}
SECTION_TITLES = [
    "1. Investigation details", "2. Dataset information", "3. Evidence inventory", "4. Original timeline",
    "5. Original inferences", "6. Peer critiques", "7. Alternative explanations", "8. Revised timeline",
    "9. Revision history", "10. Limitations", "11. Final conclusion",
]


class InstanceReset(Exception):
    """The serverless instance was replaced and our test data vanished (temporary storage)."""


class StepFailed(Exception):
    pass


class Run:
    def __init__(self):
        self.client = httpx.Client(base_url=BASE, timeout=90)
        self.steps = []
        self.cid = None
        self.ids = {}

    def call(self, name, method, path, expect, headers=None, check=None, **kw):
        started = time.perf_counter()
        r = self.client.request(method, path, headers=INV if headers is None else headers, **kw)
        ms = round((time.perf_counter() - started) * 1000)
        wanted = tuple(expect) if isinstance(expect, (list, tuple)) else (expect,)
        if self.cid and r.status_code == 404 and 404 not in wanted:
            raise InstanceReset(f"{name}: 404 after the test case was created")
        ok, note = r.status_code in wanted, ""
        if ok and check:
            try:
                note = check(r) or ""
            except AssertionError as exc:
                ok, note = False, f"check failed: {exc}"
        if not ok and not note:
            note = r.text[:160].replace("|", "/")
        self.steps.append({
            "n": len(self.steps) + 1, "step": name, "request": f"{method} {path}", "expected": "/".join(map(str, wanted)),
            "status": r.status_code, "ms": ms, "ok": ok, "note": note,
        })
        print(f"{'PASS' if ok else 'FAIL'}  {len(self.steps):2d}. {name} -> {r.status_code} ({ms} ms) {note}")
        if not ok:
            raise StepFailed(name)
        return r

    def scenario(self):
        c = self.call
        c("Service is up and reports temporary storage", "GET", "/api/health", 200,
          check=lambda r: "ephemeral=" + str(r.json()["ephemeral"]))
        c("Bundled demo case is present", "GET", "/api/cases", 200,
          check=lambda r: (_ for _ in ()).throw(AssertionError("DF-PBL-040 missing")) if not any(x["case_code"] == "DF-PBL-040" for x in r.json()) else "DF-PBL-040 found")
        title = "[LIVE TEST] " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + " UTC"
        r = c("Investigator creates an investigation", "POST", "/api/cases", 201, json={"title": title, "description": "Automated live test", "dataset_name": "Illustrative sample (synthetic)"})
        self.cid = r.json()["id"]
        cid = self.cid
        c("Reviewer mode cannot create an investigation", "POST", "/api/cases", 403, headers=REV, json={"title": "x"})

        data = SAMPLE.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        files = lambda: {"file": ("sample_evidence.csv", data, "text/csv")}

        def check_preview(r):
            b = r.json()
            assert b["valid_records"] == 5 and b["malformed_count"] == 1, b
            assert b["by_timezone_status"] == {"known": 4, "unknown": 1}, b["by_timezone_status"]
            assert b["sha256"] == digest, "SHA-256 differs from the local file"
            return "5 valid, 1 malformed, 1 unknown timezone, SHA-256 matches local"

        c("Preview validates, hashes, flags malformed rows (stores nothing)", "POST", f"/api/cases/{cid}/evidence/preview", 200, files=files(), check=check_preview)
        c("Nothing was stored by the preview", "GET", f"/api/cases/{cid}/evidence", 200, check=lambda r: _eq(r.json(), [], "evidence list"))
        r = c("Import evidence (original file stored by hash)", "POST", f"/api/cases/{cid}/evidence", 201, files=files(), check=lambda r: _eq(r.json()["valid_records"], 5, "valid_records"))
        evid = r.json()["evidence_id"]
        c("Importing the same file again is refused", "POST", f"/api/cases/{cid}/evidence", 409, files=files())
        c("Reviewer mode cannot import evidence", "POST", f"/api/cases/{cid}/evidence", 403, headers=REV, files={"file": ("other.csv", data + b" ", "text/csv")})
        c("A non-CSV/JSON file is rejected", "POST", f"/api/cases/{cid}/evidence", 422, files={"file": ("evil.exe", b"MZ", "application/octet-stream")})
        c("Integrity re-check of the stored file", "GET", f"/api/evidence/{evid}/verify", 200, check=lambda r: _eq(r.json()["result"], "MATCH", "verify result"))

        def check_timeline(r):
            ev = r.json()["events"]
            refs = [e["artifact_reference"] for e in ev]
            assert refs == ["EV001", "EV002", "EV003", "EV004", "EV005"], refs
            assert ev[4]["timezone_status"] == "unknown" and ev[4]["event_time_utc"] is None, ev[4]
            self.ids = {e["artifact_reference"]: e["id"] for e in ev}
            return "order EV001..EV004 then EV005 (unknown timezone, not converted)"

        c("Timeline is chronological; unknown timezone is flagged and last", "GET", f"/api/cases/{cid}/timeline", 200, check=check_timeline)
        body = {"title": "USB used around the document access", "explanation": "A USB device was connected and removed around the time a document was accessed.",
                "reasoning": "EV002 and EV004 bracket the file access EV003.", "confidence": 3}
        r = c("Create an inference with three supporting events", "POST", f"/api/cases/{cid}/inferences", 201,
              json={**body, "event_ids": [self.ids["EV002"], self.ids["EV003"], self.ids["EV004"]]}, check=lambda r: _eq(r.json()["status"], "proposed", "status"))
        iid = r.json()["id"]
        c("An inference citing a non-existent event is refused", "POST", f"/api/cases/{cid}/inferences", 422, json={**body, "event_ids": [999999]})
        c("Reviewer mode cannot create an inference", "POST", f"/api/cases/{cid}/inferences", 403, headers=REV, json={**body, "event_ids": [self.ids["EV001"]]})

        review = {"reviewer_name": "Live reviewer", "decision": "challenge", "critique": "Connection times alone do not show the device was used.",
                  "alternative_explanation": "The device was connected for charging only.", "additional_evidence": "File-copy artifacts for the device.", "confidence": 4}
        c("A challenge without an alternative explanation is refused", "POST", f"/api/inferences/{iid}/reviews", 422, headers=REV, json={**review, "alternative_explanation": ""})
        r = c("Reviewer submits a challenge with an alternative", "POST", f"/api/inferences/{iid}/reviews", 201, headers=REV, json=review)
        rid = r.json()["id"]
        c("Inference is now marked challenged", "GET", f"/api/inferences/{iid}", 200, check=lambda r: _eq(r.json()["status"], "challenged", "status"))
        c("A duplicate review in the same round is refused", "POST", f"/api/inferences/{iid}/reviews", 409, headers=REV, json=review)
        c("Investigator mode cannot submit a review", "POST", f"/api/inferences/{iid}/reviews", 403, headers=INV, json=review)

        reply = {"response": "accepted", "peer_review_id": rid, "revised_reasoning": "Connection and removal are proven; actual use is not.",
                 "revised_explanation": "A USB device was connected between 09:15 and 09:35; its use is unproven.", "new_confidence": 2}
        c("A response without a justification is refused", "POST", f"/api/inferences/{iid}/revisions", 422, json={**reply, "change_reason": ""})

        def check_reply(r):
            b = r.json()
            assert b["inference"]["status"] == "revised" and b["inference"]["confidence"] == 2, b["inference"]
            assert b["inference"]["original_reasoning"] == body["reasoning"], "original reasoning was overwritten"
            return "status revised; original reasoning preserved"

        c("Investigator accepts the challenge and revises", "POST", f"/api/inferences/{iid}/revisions", 201, json={**reply, "change_reason": "The reviewer is right: use is unproven."}, check=check_reply)
        c("The same review cannot be answered twice", "POST", f"/api/inferences/{iid}/revisions", 409, json={**reply, "change_reason": "again"})

        def check_history(r):
            h = r.json()
            assert [s["kind"] for s in h["steps"]] == ["review", "revision"], h["steps"]
            assert h["original"]["reasoning"] == body["reasoning"] and h["current"]["status"] == "revised"
            return "original -> challenge -> response -> current"

        c("History keeps original, challenge, response and current", "GET", f"/api/inferences/{iid}/history", 200, check=check_history)

        def check_audit(r):
            actions = [a["action_type"] for a in reversed(r.json())]
            want = ["case_created", "evidence_imported", "inference_created", "review_submitted", "revision_recorded"]
            assert actions == want, actions
            return " > ".join(actions)

        c("Audit trail recorded every action in order", "GET", f"/api/cases/{cid}/audit", 200, check=check_audit)

        def check_pdf(r):
            assert r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF"), "not a PDF"
            assert len(r.content) > 3000, len(r.content)
            missing = [t for t in SECTION_TITLES if t.encode() not in r.content]
            assert not missing, missing
            return f"{len(r.content)} bytes, all 11 section headings present"

        c("Investigator generates the PDF report", "GET", f"/api/cases/{cid}/report", 200, check=check_pdf)
        c("Reviewer mode cannot generate the report", "GET", f"/api/cases/{cid}/report", 403, headers=REV)
        c("The audit trail cannot be deleted", "DELETE", f"/api/cases/{cid}/audit", 405)
        c("The bundled demo case is untouched", "GET", "/api/cases/1/summary", 200,
          check=lambda r: _eq((r.json()["timeline"]["total"], r.json()["inferences"]["total"]), (25, 9), "demo case (events, inferences)"))
        c("Dashboard reflects both investigations", "GET", "/api/dashboard", 200,
          check=lambda r: _gte(r.json()["investigations"], 2, "investigations"))


def _eq(got, want, what):
    assert got == want, f"{what}: got {got!r}, expected {want!r}"
    return f"{what} = {got}"


def _gte(got, want, what):
    assert got >= want, f"{what}: got {got!r}, expected >= {want!r}"
    return f"{what} = {got}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    resets, run, error = 0, None, None
    for attempt in range(1, 4):
        run = Run()
        try:
            print(f"--- attempt {attempt} against {BASE}")
            run.scenario()
            error = None
            break
        except InstanceReset as exc:
            resets += 1
            error = f"instance reset: {exc}"
            print("RESET", exc, "- retrying with a fresh test case")
        except StepFailed as exc:
            error = f"step failed: {exc}"
            break
    passed = sum(s["ok"] for s in run.steps)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# ChronoPeer live test report", "", f"- Site: {BASE}", f"- Run at: {stamp}",
        f"- Result: **{'ALL PASSED' if error is None else 'FAILED'}** ({passed} of {len(run.steps)} steps passed)",
        f"- Serverless instance resets during the run: {resets}", "",
        "| # | Step | Request | Expected | Got | Time | Result | Detail |", "|---|---|---|---|---|---|---|---|",
    ]
    for s in run.steps:
        lines.append(f"| {s['n']} | {s['step']} | `{s['request']}` | {s['expected']} | {s['status']} | {s['ms']} ms | {'PASS' if s['ok'] else 'FAIL'} | {s['note']} |")
    if error:
        lines += ["", f"Stopped: {error}"]
    (OUT / "live_test_report.md").write_text(chr(10).join(lines) + chr(10), encoding="utf8")
    (OUT / "live_test_results.json").write_text(json.dumps({"site": BASE, "run_at": stamp, "resets": resets, "error": error, "steps": run.steps}, indent=1), encoding="utf8")
    print(f"{passed}/{len(run.steps)} steps passed" + ("" if error is None else f"  ({error})"))
    return 0 if error is None else 1


if __name__ == "__main__":
    sys.exit(main())
