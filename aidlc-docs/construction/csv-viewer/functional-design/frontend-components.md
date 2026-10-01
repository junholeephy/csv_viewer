# Frontend Components — csv-viewer (Streamlit)

## Layout

```
+--------------------------------------------------------------+
| Sidebar                  | Main                              |
|  root: <dir>             |  <file name>  (size)              |
|  [file selectbox]        |  [progress bar] n rows / done     |
|  encoding [auto|...]     |  [|<] [<] [page #] [>] [>|] rows  |
|  delimiter [auto|...]    |  warnings (ragged, decode)        |
|  page size (50/100/500)  |  tabs: [Table] [Column summary]   |
|  [x] raw view            |                                   |
+--------------------------------------------------------------+
```

## Components and State

| Component | Streamlit | Reads | Writes (session_state) |
|---|---|---|---|
| FilePicker | `st.sidebar.selectbox` | `list_data_files(root)` | `file` (변경 시 `page=0`) |
| FormatControls | `st.sidebar.selectbox` x2 | `sniff_format` 결과(auto 표시용) | `encoding`, `delimiter` (변경 시 `page=0`) |
| PageSizeControl | `st.sidebar.segmented_control` 또는 `radio` | - | `page_size`, `page` 재계산(R-P1) |
| RawToggle | `st.sidebar.toggle` | - | `raw` |
| IndexProgressPanel | `@st.fragment(run_every=0.5)` 안 `st.progress` + caption | `job.progress()` | 완료를 처음 본 순간 `index_done=True` 후 `st.rerun()` (전체 1회) |
| Pager | `st.columns` + `st.button` x4 + `st.number_input` | `max_reachable_page`, `page_count` | `page` |
| WarningsBar | `st.warning` | `PageWarnings` | - |
| TableView | `st.dataframe(styler, column_config=..., use_container_width=True, height=고정)` | page frame, types, null mask | - |
| SummaryView | `st.dataframe(summary)` + `st.selectbox(컬럼)` + `st.bar_chart`/`st.line_chart` | `summarize`, chart data | - |

## Interaction Flows
1. **최초 진입**: root 검증 → 파일 목록 → 첫 파일 미선택 상태(placeholder) → 안내 문구.
2. **파일 선택**: sniff → header → get_job(캐시) → page 0 즉시 렌더 → 진행 fragment 가 0.5s 마다 갱신.
3. **다음/이전**: `page±1` (경계·reachable 검사) → 전체 rerun → `read_rows` 1회.
4. **페이지 번호 입력**: `min=1, max=max_reachable_page+1` (표시는 1-based) → 변경 시 rerun.
5. **인덱싱 완료**: fragment 가 감지 → `st.rerun()` → Pager 의 "끝" 활성화, 총 행/페이지 표시, fragment 는 더 이상 run_every 로 돌지 않음 (완료 시 정적 표시로 전환).
6. **포맷 변경**: 새 캐시 키 → 이전 job `stop()` → page 0.

## Validation Rules (UI)
- 페이지 입력은 정수, 범위 밖 값은 위젯이 clamp.
- `--root` 미존재 시 다른 위젯을 그리지 않는다.

## Backend Integration
- API 없음. 모든 호출은 같은 프로세스의 C1–C4 함수 (`component-methods.md`).
