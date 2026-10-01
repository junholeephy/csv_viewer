# Code Summary — csv-viewer

## Modified
- `src/core/load.py` — `load_csv` 는 그대로. 추가: `CsvFormat`, `DELIMITERS`, `ENCODINGS`, `sniff_format`, `iter_row_offsets`(따옴표 인지 바이트 스캐너 + 따옴표 없는 줄 빠른 경로), `read_rows`, `normalize_header`, `read_header`. `csv.field_size_limit` 상향.
- `requirements.txt` — `streamlit==1.64.0`, `pandas==3.0.6`
- `requirements-dev.txt` — `hypothesis==6.168.3`
- `tests/conftest.py` — Hypothesis 프로파일(default: print_blob, ci: derandomize)
- `TODO.md` — "5. CSV 뷰어 띄우기" (venv 직접 활성화, localhost 바인딩)
- `SCAFFOLD.md` — 파일 지도에 뷰어 항목

## Created
- `src/app.py` — Streamlit UI (C5)
- `src/core/viewer/__init__.py`, `files.py` (C4), `jobs.py` (C2), `present.py` (C3)
- `tests/strategies.py` — 공용 Hypothesis 전략 `csv_cases`, `fields`
- `tests/test_load_paged.py` (예제 15), `tests/test_load_paged_pbt.py` (TP-1/2/3)
- `tests/test_viewer.py` (예제 21), `tests/test_viewer_pbt.py` (TP-4/5/6/7/8)
- `tests/test_app.py` — Streamlit AppTest 스모크 4
- `tools/bench_viewer.py` — 성능 측정 (export-ignore 대상 `tools/`)

## Deviations from design (구현 중 확정·변경된 것)
| 항목 | 설계 | 구현 | 이유 |
|---|---|---|---|
| `coerce` 반환 | DataFrame | `(DataFrame, applied_types)` | 변환 실패 컬럼을 "str" 로 내린 사실을 표/요약이 알아야 함 |
| `offset_of_row(0)` | 체크포인트 조회 | 항상 `data_start` | **PBT 발견 결함**: 헤더만 있는 파일에서 None. 회귀 예제 테스트 추가 |
| 진행률 | 콜백 | 마지막 행 오프셋을 `bytes_done` 근사로 사용 | 스캐너 시그니처 단순화. 완료 시 정확히 파일 크기 |
| 추가 API | - | `IndexJob.join`, `abandoned`, `last_reachable_page`; `present.style`, `chart_data`, `page_warnings`, `data_columns` | UI·테스트에 필요 |
| 다음 버튼 | 인덱스 도달 시 활성 | 항상 활성, 미도달이면 토스트 안내 | 인덱싱 중 버튼 상태가 rerun 전까지 갱신되지 않는 문제 회피 |
| 캐시 무효화 | 이전 작업 stop | stop + `cache_resource(validate=not abandoned)` | 멈춘 작업으로 돌아왔을 때 새로 만들도록 |

## Known approximations / limits
- 단독 CR 줄 종결자 미지원 (R-D1). UTF-16/32 미지원 (R-D4).
- 디코딩 오류 수 = 페이지 내 U+FFFD 개수 (원본에 그 문자가 있으면 과대).
- 타입 추론·요약·차트는 현재 페이지 기준.
- `data-testid` 규칙은 Streamlit 에서 직접 지정 불가 → 모든 위젯에 고정 `key` 부여(`file`, `encoding`, `delimiter`, `page_size`, `raw`, `page_no`, `nav_first|prev|next|last`, `table`, `summary`, `chart_column`).
