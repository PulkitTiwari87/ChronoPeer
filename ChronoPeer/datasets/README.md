# Datasets

`sample_exports/sysmon_iewin7_export.csv` is the demo evidence in ChronoPeer's import format (`timestamp, event_type, description, source, artifact_id`). Regenerate it with:

```bash
python -I datasets/make_sysmon_export.py
```

`sample_exports/source/` holds the project's original CSVs it is derived from (timeline, evidence log, inference registers, critique, revision log), unchanged. See `docs/dataset_documentation.md` for provenance, the extraction process and every mapping made. Do not commit disk images, private evidence or uploaded files here.
