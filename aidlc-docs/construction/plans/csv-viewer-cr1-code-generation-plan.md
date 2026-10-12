# Code Generation Plan — CR1 (row detail panel, column ordering)

Approval: user answered "추천대로" to cr1-questions.md (all A); plan follows those answers 1:1.

- [x] Step 1 — `src/core/viewer/present.py`: `CELL_LIMIT=300`, `LONG_TEXT=200`, `truncate(frame, limit)`, `is_long(value)`, `parse_json(value)`, `row_detail(frame, position, columns)` → (short DataFrame, long list). [FR-12, FR-13]
- [x] Step 2 — `src/app.py`: per-file column order/pin controls in sidebar (`order::<file>`, `pin::<file>`, reset), `column_order` + `column_config(pinned)` on tables, single-row selection (`on_select="rerun"`, key includes file/page/page_size), detail panel (`st.dataframe` short values, `st.code(wrap_lines)` long values, `st.json` expander), summary/chart follow order. [FR-12, FR-13, FR-14]
- [x] Step 3 — tests: `tests/test_viewer.py` examples (truncate, is_long, parse_json, row_detail); `tests/test_viewer_pbt.py` TP-9 truncate invariant (len ≤ limit+1, prefix preserved, short values untouched); `tests/test_app.py` column order + pin + persistence across pages, detail panel via selection state.
- [x] Step 4 — docs: README (화면/한계), code-summary addendum; full test run; real server check.
