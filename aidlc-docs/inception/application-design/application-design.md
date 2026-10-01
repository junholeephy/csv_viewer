# Application Design — csv-viewer (Consolidated)

## Decisions (application-design-plan.md, 전부 추천안 A)
1. 페이지 리더는 `src/core/load.py` 확장 — 포맷 지식 한 곳 원칙 유지
2. 백그라운드 인덱싱 = 스레드 소유 `IndexJob` + `st.cache_resource` + `st.fragment(run_every)`
3. 인덱스 = 50행 간격 체크포인트 (페이지 크기 50/100/500 의 공약수)
4. 뷰어 = `src/core/viewer/{jobs,present,files}.py` + UI 전용 `src/app.py`
5. 루트 = CLI 인자 `streamlit run src/app.py -- --root <dir>` (기본 cwd)

## Components
C1 Reader(`load.py`) · C2 IndexJob(`viewer/jobs.py`) · C3 Presenter(`viewer/present.py`) · C4 File Catalog(`viewer/files.py`) · C5 App(`src/app.py`). 상세: `components.md`.

## Key Interfaces
`sniff_format`, `read_header`, `iter_row_offsets`, `read_rows` / `IndexJob.start|stop|progress|offset_of_row` / `to_frame`, `infer_types`, `coerce`, `null_mask`, `summarize` / `list_data_files`, `resolve_within`. 상세: `component-methods.md`.

## Orchestration
S1 파일 열기 → S2 페이지 표시(첫 페이지는 인덱스 불필요) → S3 진행률 fragment → S4 파일/포맷 변경 시 이전 작업 중단. 상세: `services.md`.

## Dependencies
단방향 `app → viewer.* → load/schema`. 배치 CLI 는 뷰어를 import 하지 않아 streamlit/pandas 없이도 동작. 상세: `component-dependency.md`.

## Requirements Traceability
| Req | Component |
|---|---|
| FR-1 | C4, C5 |
| FR-2 | C1 `sniff_format`, C5 사이드바 |
| FR-3, FR-4 | C1 `read_header`/`read_rows`, S2 |
| FR-5, FR-6 | C2, S3, C5 내비게이션 |
| FR-7, FR-8, FR-9, FR-10 | C3, C5 (`st.dataframe` 내장 정렬) |
| FR-11 | C1 예외 → C5 안내, C3 열 수 불일치 표시 |
| NFR-1, NFR-2 | 체크포인트 seek, 페이지분만 메모리 |
| NFR-3 | `st.cache_resource` 키 (path, mtime, size, fmt, data_start) |
| NFR-4, NFR-6 | 배치 경로 불변, 단방향 의존 |
| NFR-7 | C1 PBT 대상 (Functional Design 에서 성질 정의) |

## Validation
- 모든 FR/NFR 이 최소 하나의 컴포넌트에 매핑됨
- 순환 의존 없음
- Streamlit 의존은 C5 하나로 격리 → C1–C4 는 pytest 로 단위 테스트 가능
