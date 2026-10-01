# Code Generation Plan — csv-viewer (single source of truth)

## Unit Context
- **Unit**: csv-viewer (single unit, brownfield, workspace root `/Users/junho/coding_work/csv_viewer`)
- **Requirements covered**: FR-1..FR-11, NFR-1..NFR-7 (requirements.md)
- **Design inputs**: application-design/*, construction/csv-viewer/functional-design/*, nfr-requirements/*
- **Dependencies**: none on other units. Reuses `core.schema.NULL_TOKENS` / `is_null`.
- **Interfaces**: per `component-methods.md`
- **Approval**: pre-approved by user ("너의 추천사항을 받아 들일테니 ... 끝까지 구현해줘", 2026-10-01T07:37:40Z)

## Steps
- [x] **Step 1 — Dependencies**: modify `requirements.txt` (streamlit==1.64.0, pandas==3.0.6), `requirements-dev.txt` (+ hypothesis==6.168.3). [NFR-5]
- [x] **Step 2 — Reader (C1)**: modify `src/core/load.py` — add `CsvFormat`, `sniff_format`, `read_header`, `iter_row_offsets` (quote-aware byte scanner, newline fast path), `read_rows`, header normalisation. Keep `load_csv` unchanged. [FR-2, FR-3, FR-4, R-D*, R-R1, R-H1]
- [x] **Step 3 — Reader tests**: create `tests/strategies.py` (reusable `csv_tables` Hypothesis strategy, PBT-07), `tests/test_load_paged.py` (example tests), `tests/test_load_paged_pbt.py` (TP-1, TP-2, TP-3). Register Hypothesis profiles in `tests/conftest.py` (PBT-08).
- [x] **Step 4 — File catalog (C4)**: create `src/core/viewer/__init__.py`, `src/core/viewer/files.py`. [FR-1, R-F1, R-F2]
- [x] **Step 5 — IndexJob (C2)**: create `src/core/viewer/jobs.py`. [FR-5, FR-6, L4, L5]
- [x] **Step 6 — Presenter (C3)**: create `src/core/viewer/present.py` (`to_frame`, `infer_types`, `coerce`, `null_mask`, `summarize`, `chart_data`, `page_warnings`). [FR-7, FR-8, FR-9, R-R3, R-T*]
- [x] **Step 7 — Viewer tests**: create `tests/test_viewer.py` (examples for files/jobs/present) and `tests/test_viewer_pbt.py` (TP-4, TP-5, TP-6, TP-7, TP-8).
- [x] **Step 8 — App (C5)**: create `src/app.py` (Streamlit UI, `--root`, cache_resource, fragment progress, pager, table/summary tabs, error handling). [FR-1..FR-11, frontend-components.md]
- [x] **Step 9 — App smoke test**: create `tests/test_app.py` using `streamlit.testing.v1.AppTest` (renders first page from a synthetic CSV in tmp_path, pager next works); skipped if streamlit missing.
- [x] **Step 10 — Bench + run script**: create `tools/bench_viewer.py` (synthetic 1GB CSV in a temp dir, measures P-1..P-3; dev-only, `tools/` already export-ignored) and `run_viewer.sh`? → NO: per `todo/scripting.md` run scripts live in the work folder, not in the repo; document the command in TODO.md instead.
- [x] **Step 11 — Docs**: modify `TODO.md` (viewer launch, venv activation since `run.py` venv switch does not apply, localhost binding), `SCAFFOLD.md` (file map rows for viewer). Create `aidlc-docs/construction/csv-viewer/code/code-summary.md`.
- [x] **Step 12 — Compliance check**: no workflow vocabulary (C9 words) / personal absolute paths / LLM imports in `src/`; no duplicate files; no data files created in repo.

## Story Traceability
User Stories skipped — traceability is to FR/NFR IDs above.
