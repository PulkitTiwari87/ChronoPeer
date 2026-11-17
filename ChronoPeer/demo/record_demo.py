#!/usr/bin/env python3
"""Record a captioned walkthrough of the live ChronoPeer site (Chrome driven by Playwright).

Usage:  python demo/record_demo.py [base_url]       (default https://chronopeer.vercel.app)
Needs:  playwright (Python), Google Chrome, ffmpeg on PATH, httpx
Writes (demo/output/): chronopeer_demo.mp4 (English captions burned in), chronopeer_demo.srt,
        scenes.json, chronopeer-report.pdf (downloaded in the last step), screenshots/*.png
Captions are drawn inside the page, so the recording and its subtitles can never drift apart.
"""
import json
import shutil
import subprocess
import sys
import textwrap
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://chronopeer.vercel.app").rstrip("/")
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
SHOTS = OUT / "screenshots"
TMP = OUT / "_video_tmp"
SAMPLE = HERE / "sample_evidence.csv"
W, H = 1280, 720
WAIT = 30000

OVERLAY_JS = r"""
(() => {
  const STYLE = `
  #cp-cap{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);width:min(1040px,calc(100% - 100px));z-index:2147483647;
    background:rgba(20,20,22,.9);color:#fff;font:500 25px/1.38 -apple-system,"Segoe UI",system-ui,sans-serif;padding:16px 26px;
    border-radius:18px;text-align:center;box-shadow:0 8px 30px rgba(0,0,0,.35);display:none;pointer-events:none}
  #cp-step{position:fixed;top:14px;left:14px;z-index:2147483647;background:#0071e3;color:#fff;font:600 16px system-ui,sans-serif;
    padding:7px 16px;border-radius:999px;display:none;pointer-events:none}
  #cp-cursor{position:fixed;z-index:2147483647;width:24px;height:24px;border-radius:50%;background:rgba(255,196,0,.6);border:2px solid #fff;
    box-shadow:0 0 0 2px rgba(0,0,0,.4);transform:translate(-50%,-50%);pointer-events:none;left:-60px;top:-60px;display:none;transition:transform 120ms}
  #cp-title{position:fixed;inset:0;z-index:2147483646;background:#000;color:#fff;display:none;flex-direction:column;align-items:center;
    justify-content:center;text-align:center;font-family:-apple-system,"Segoe UI",system-ui,sans-serif;padding:60px 60px 150px}`;
  function mount() {
    if (document.getElementById("cp-cap") || !document.documentElement) return;
    const s = document.createElement("style"); s.textContent = STYLE; document.documentElement.appendChild(s);
    for (const id of ["cp-title", "cp-cap", "cp-step", "cp-cursor"]) {
      const d = document.createElement("div"); d.id = id; document.documentElement.appendChild(d);
    }
    try { const saved = sessionStorage.getItem("cp-cap-state"); if (saved) { const [t, st] = JSON.parse(saved); apply(t, st); } } catch (e) {}
  }
  function apply(text, step) {
    const c = document.getElementById("cp-cap"), p = document.getElementById("cp-step");
    if (!c || !p) return;
    c.textContent = text || ""; c.style.display = text ? "block" : "none";
    p.textContent = step || ""; p.style.display = step ? "block" : "none";
  }
  window.__capSet = (text, step) => {
    mount();
    try { sessionStorage.setItem("cp-cap-state", JSON.stringify([text, step])); } catch (e) {}
    apply(text, step);
  };
  window.__card = (title, sub, foot) => {
    mount();
    const c = document.getElementById("cp-title");
    c.innerHTML = '<div style="font:700 80px/1.05 -apple-system,Segoe UI,system-ui,sans-serif;letter-spacing:-.03em">' + title + '</div>' +
      '<div style="font:400 32px/1.35 system-ui,sans-serif;color:#a1a1a6;margin-top:22px;max-width:920px">' + sub + '</div>' +
      '<div style="font:500 22px system-ui,sans-serif;color:#2997ff;margin-top:34px">' + foot + '</div>';
    c.style.display = "flex";
  };
  window.__cardHide = () => { const c = document.getElementById("cp-title"); if (c) c.style.display = "none"; };
  window.addEventListener("mousemove", (e) => {
    const c = document.getElementById("cp-cursor");
    if (c) { c.style.display = "block"; c.style.left = e.clientX + "px"; c.style.top = e.clientY + "px"; }
  }, true);
  window.addEventListener("mousedown", () => {
    const c = document.getElementById("cp-cursor");
    if (c) { c.style.transform = "translate(-50%,-50%) scale(1.9)"; setTimeout(() => { c.style.transform = "translate(-50%,-50%) scale(1)"; }, 240); }
  }, true);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
"""


class Recorder:
    def __init__(self, page):
        self.page = page
        self.t0 = time.monotonic()
        self.scenes = []

    def now(self):
        return time.monotonic() - self.t0

    def pause(self, ms):
        self.page.wait_for_timeout(ms)

    def check_no_error(self):
        alerts = self.page.locator("[role=alert]")
        if alerts.count():
            raise RuntimeError("UI error shown on the page: " + alerts.first.inner_text()[:200])

    @contextmanager
    def scene(self, label, text, shot=None):
        start = self.now()
        self.page.evaluate("([t, s]) => window.__capSet(t, s)", [text, label])
        yield
        need = len(text) / 13.0 + 1.5  # about 13 characters per second is comfortable to read
        spent = self.now() - start
        if spent < need:
            self.page.wait_for_timeout(int((need - spent) * 1000))
        self.check_no_error()
        if shot:
            self.page.screenshot(path=str(SHOTS / shot))
        self.scenes.append({"label": label, "text": text, "start": round(start, 2), "end": round(self.now(), 2)})

    def click(self, locator):
        locator.scroll_into_view_if_needed(timeout=WAIT)
        box = locator.bounding_box()
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=16)
        self.pause(220)
        self.page.mouse.down()
        self.pause(70)
        self.page.mouse.up()
        self.pause(320)

    def hover(self, locator):
        locator.scroll_into_view_if_needed(timeout=WAIT)
        box = locator.bounding_box()
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=16)
        self.pause(250)

    def type_into(self, locator, text, replace=False):
        self.click(locator)
        if replace:
            self.page.keyboard.press("Control+A")
        locator.press_sequentially(text, delay=26)
        self.pause(250)

    def choose(self, locator, value):
        self.hover(locator)
        locator.select_option(value)
        self.pause(250)

    def scroll(self, pixels, steps=4):
        for _ in range(steps):
            self.page.mouse.wheel(0, pixels)
            self.pause(450)


def see(locator):
    expect(locator).to_be_visible(timeout=WAIT)


def srt_time(seconds):
    ms = int(round(seconds * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def record_once(p):
    for _ in range(4):  # wake the serverless function so the first screens are not slow
        httpx.get(BASE + "/api/health", timeout=60)
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(
        viewport={"width": W, "height": H}, record_video_dir=str(TMP), record_video_size={"width": W, "height": H},
        accept_downloads=True, color_scheme="light", locale="en-US",
    )
    ctx.add_init_script(OVERLAY_JS)
    page = ctx.new_page()
    page.set_default_timeout(WAIT)
    rec = Recorder(page)
    nav = lambda name: rec.click(page.get_by_role("navigation", name="Pages").get_by_role("link", name=name, exact=True))
    mode = page.get_by_role("group", name="Operating mode")
    code = "DEMO-" + datetime.now().strftime("%H%M%S")

    page.goto(BASE + "/", wait_until="load")
    see(page.get_by_role("heading", level=1))
    rec.pause(600)

    with rec.scene("Introduction", "ChronoPeer rebuilds an incident timeline from evidence, then makes every conclusion face a peer challenge before it is accepted.", "01-intro.png"):
        page.evaluate("window.__card('ChronoPeer', 'Forensic incident timelines with built-in peer review', 'Live demo: chronopeer.vercel.app')")
    page.evaluate("window.__cardHide()")

    with rec.scene("1 of 14 · Dashboard", "The dashboard counts investigations, evidence files, events, inferences and reviews still waiting. This live site already holds a real case.", "02-dashboard.png"):
        expect(page.get_by_role("heading", level=1)).to_contain_text("Challenge every inference", timeout=WAIT)
        see(page.get_by_text("Awaiting review").first)
        rec.page.mouse.move(420, 300, steps=30)

    with rec.scene("2 of 14 · Real case timeline", "That real case has 25 Sysmon events from one Windows host, ordered by the time each event happened and plotted on a single timeline.", "03-real-timeline.png"):
        nav("Timeline")
        page.wait_for_function("document.querySelectorAll('.js-plotly-plot .point').length >= 25", timeout=45000)
        rec.pause(1500)
        rec.scroll(240, steps=3)

    with rec.scene("3 of 14 · Real case history", "Every inference was challenged. For I4 the history shows the original claim, the reviewer's challenge, the author's replies, and the claim retained.", "04-real-history.png"):
        nav("Revisions")
        history = page.locator("details", has_text="Full revision history").nth(3)
        see(history)
        rec.click(history.locator("summary"))
        see(history.get_by_text("Current conclusion"))
        history.scroll_into_view_if_needed()
        rec.scroll(220, steps=2)

    with rec.scene("4 of 14 · New investigation", "Now a new investigation. In Investigator mode we record the case: an ID, a title, a description and the dataset used.", "05-new-case.png"):
        nav("Case")
        rec.click(page.get_by_role("button", name="New investigation"))
        rec.type_into(page.get_by_label("Case ID (optional label)"), code)
        rec.type_into(page.get_by_label("Title"), "Laptop USB data-copy check")
        rec.type_into(page.get_by_label("Description"), "Did a USB device copy a document? Illustrative scenario for this demo.")
        rec.type_into(page.get_by_label("Dataset information"), "Illustrative sample (synthetic)")
        rec.click(page.get_by_role("button", name="Create investigation"))
        page.wait_for_function("[...document.querySelectorAll('header select option')].some(o => o.selected && o.textContent.includes('%s'))" % code, timeout=WAIT)

    with rec.scene("5 of 14 · Evidence preview", "Uploading is two steps. The preview hashes the file with SHA-256, validates each row, flags the bad one, and keeps a timestamp with no timezone as unknown.", "06-preview.png"):
        nav("Evidence")
        rec.hover(page.locator("input[type=file]"))
        page.locator("input[type=file]").set_input_files(str(SAMPLE))
        rec.pause(500)
        rec.click(page.get_by_role("button", name="Preview", exact=True))
        see(page.get_by_text("valid records"))
        rec.scroll(260, steps=2)

    with rec.scene("6 of 14 · Import", "Confirm imports the valid rows. The original file is stored untouched, named by its hash, so it can always be re-checked.", "07-imported.png"):
        rec.click(page.get_by_role("button", name="Confirm import"))
        see(page.get_by_text("Imported 5 events"))
        see(page.get_by_role("button", name="Re-check"))

    with rec.scene("7 of 14 · Integrity check", "Re-check recomputes the SHA-256 of the stored file. MATCH means the evidence is exactly what was imported.", "08-integrity.png"):
        rec.click(page.get_by_role("button", name="Re-check"))
        see(page.get_by_text("MATCH", exact=True))

    with rec.scene("8 of 14 · Timeline", "The order is deterministic: known UTC times first, then the unknown-timezone event, flagged and never guessed.", "09-timeline.png"):
        nav("Timeline")
        page.wait_for_function("document.querySelectorAll('.js-plotly-plot .point').length >= 4", timeout=45000)
        rec.pause(1200)
        rec.scroll(300, steps=2)

    with rec.scene("9 of 14 · Inference", "The investigator records an inference: what happened, why, a confidence from 1 to 5, and at least one supporting event.", "10-inference.png"):
        nav("Inferences")
        rec.click(page.get_by_role("button", name="Add inference"))
        rec.type_into(page.get_by_label("Title"), "USB device used around the document access")
        rec.type_into(page.get_by_label("Explanation"), "A USB device was connected and removed around the time a document was accessed.")
        rec.type_into(page.get_by_label("Reasoning"), "EV002 and EV004 bracket the file access EV003.")
        for ref in ("EV002", "EV003", "EV004"):
            rec.click(page.locator("label", has_text=ref).locator("input[type=checkbox]"))
        rec.click(page.get_by_role("button", name="Create inference"))
        see(page.get_by_role("heading", name="USB device used around the document access"))

    with rec.scene("10 of 14 · Peer reviewer mode", "Switch to Peer reviewer mode. The current mode is always shown, and each mode can only do its own actions.", "11-reviewer-mode.png"):
        rec.click(mode.get_by_role("button", name="Peer reviewer"))
        rec.type_into(page.get_by_label("Peer reviewer name"), "Dr. Rivera", replace=True)
        nav("Peer review")
        expect(page.get_by_role("heading", level=1)).to_contain_text("Challenge every inference", timeout=WAIT)
        see(page.get_by_label("Why the conclusion may be unsupported"))

    with rec.scene("11 of 14 · Challenge", "The reviewer must give a disposition. A challenge needs a reason, an alternative explanation, and the evidence that would settle it.", "12-challenge.png"):
        rec.type_into(page.get_by_label("Why the conclusion may be unsupported"), "Connection times alone do not show the device was used to copy anything.")
        rec.type_into(page.get_by_label("Alternative explanation"), "The device was connected for charging only.")
        rec.type_into(page.get_by_label("Additional evidence needed"), "File-copy artifacts for the device's drive letter.")
        rec.choose(page.get_by_label("Your confidence (1–5)"), "4")
        rec.click(page.get_by_role("button", name="Submit review"))
        see(page.get_by_text("Review recorded."))

    with rec.scene("12 of 14 · Investigator responds", "Back as investigator: accept the challenge, revise the reasoning and confidence, and justify the change. The original stays on record.", "13-response.png"):
        rec.click(mode.get_by_role("button", name="Investigator"))
        nav("Revisions")
        see(page.get_by_role("button", name="Record response"))
        rec.type_into(page.get_by_label("Revised reasoning"), "Connection and removal are proven; actual use is not.", replace=True)
        rec.choose(page.get_by_label("Confidence (1–5)"), "2")
        rec.type_into(page.get_by_label("Justification (required)"), "The reviewer is right: the logs do not show a file copy.")
        rec.click(page.get_by_role("button", name="Record response"))
        see(page.locator("section").get_by_text("revised", exact=True).first)

    with rec.scene("13 of 14 · Revision history", "The history now reads: original conclusion, the challenge, the response, and the current conclusion. Nothing was overwritten.", "14-history.png"):
        details = page.locator("details", has_text="Full revision history").first
        rec.click(details.locator("summary"))
        see(details.get_by_text("Current conclusion"))
        details.scroll_into_view_if_needed()
        rec.scroll(200, steps=2)

    with rec.scene("14 of 14 · Report", "Finally the investigator generates a PDF with 11 sections, from evidence and timeline to critiques, revisions, limitations and the conclusion.", "15-report.png"):
        nav("Report")
        see(page.get_by_role("button", name="Generate PDF report"))
        with page.expect_download(timeout=60000) as download:
            rec.click(page.get_by_role("button", name="Generate PDF report"))
        download.value.save_as(str(OUT / "chronopeer-report.pdf"))
        see(page.get_by_text("Report downloaded."))

    with rec.scene("Summary", "Every action is written to an append-only audit log. This hosted demo uses temporary storage, so run ChronoPeer locally to keep your work.", "16-outro.png"):
        page.evaluate("window.__card('Thank you', 'Evidence in. Timeline built. Every conclusion challenged, revised and reported.', 'ChronoPeer')")

    video = page.video
    ctx.close()
    browser.close()
    return rec, Path(video.path())


def export(rec, webm):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found on PATH")
    lead = max(rec.scenes[0]["start"] - 0.3, 0)
    mp4 = OUT / "chronopeer_demo.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-ss", f"{lead:.2f}", "-i", str(webm), "-vf", "fps=25,format=yuv420p",
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", str(mp4)],
        check=True,
    )
    cues = []
    for i, s in enumerate(rec.scenes, 1):
        start, end = max(s["start"] - lead, 0), max(s["end"] - lead, 0)
        body = chr(10).join(textwrap.wrap(s["text"], 64))
        cues.append(f"{i}{chr(10)}{srt_time(start)} --> {srt_time(end)}{chr(10)}{body}{chr(10)}")
    (OUT / "chronopeer_demo.srt").write_text((chr(10) * 1).join(cues), encoding="utf8")
    (OUT / "scenes.json").write_text(json.dumps({"site": BASE, "trim_seconds": round(lead, 2), "scenes": rec.scenes}, indent=1), encoding="utf8")
    return mp4


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    last = None
    with sync_playwright() as p:
        for attempt in range(1, 4):
            try:
                print(f"--- recording attempt {attempt} against {BASE}")
                rec, webm = record_once(p)
                mp4 = export(rec, webm)
                shutil.rmtree(TMP, ignore_errors=True)
                print("wrote", mp4, f"({mp4.stat().st_size // 1024} KB)")
                for s in rec.scenes:
                    print(f"  {s['start']:7.1f}s  {s['label']}")
                return 0
            except Exception as exc:  # the live site uses temporary storage: retry on a fresh case if it resets
                last = exc
                print("attempt failed:", repr(exc)[:300])
    print("giving up:", last)
    return 1


if __name__ == "__main__":
    sys.exit(main())
