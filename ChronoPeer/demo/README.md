# Live test and demo video

Both scripts work against the deployed site (default `https://chronopeer.vercel.app`) and can be pointed at a local server instead.

| File | What it does |
|---|---|
| `live_test.py` | 30-step end-to-end test over the public API: import, timeline, inference, review, revision, audit and PDF, plus 13 deliberate refusals (wrong role, duplicate, invalid input). Writes `output/live_test_report.md`. |
| `record_demo.py` | Drives the real web UI in Chrome and records one continuous video with English captions burned in, a visible cursor, a matching `.srt`, and a screenshot per step. |
| `sample_evidence.csv` | Synthetic evidence used by both (illustrative records, one row without a timezone, one malformed row). |

```bash
.venv\Scripts\python.exe demo\live_test.py https://chronopeer.vercel.app
python demo\record_demo.py https://chronopeer.vercel.app    # needs playwright, Google Chrome and ffmpeg
```

The hosted site uses temporary storage, so a test run may be wiped when the free server restarts; both scripts retry on a fresh case if that happens mid-run.
