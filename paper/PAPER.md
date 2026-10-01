# Paper supplement

Full publishable text is `../README.md` (§1–12 + References + Citation).

Submission checklist:
- [x] Every number traces to `experiments/results.json` (rerun via `docker compose up --build bench`)
- [x] Every algorithm traces to `tests/test_correctness.py` (8/8) + dual-checker in `benchmarks/run_all.py`
- [x] Live provenance logged: SNAP `email-Eu-core` SHA `6ee15a6c…` + Yahoo AAPL SHA `84f48a2d…`
- [x] Reproducibility: pinned base, locked requirements, `SOURCE_DATE_EPOCH`, one-command rerun
- [x] Limitations + 5 PhD extensions (§11–12)
