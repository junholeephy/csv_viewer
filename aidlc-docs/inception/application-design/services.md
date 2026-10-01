# Services / Orchestration — csv-viewer

별도 서비스 계층은 두지 않는다(YAGNI). 오케스트레이션은 `src/app.py` 의 `main()` 한 함수가 맡고,
각 단계는 Streamlit 비의존 컴포넌트를 호출한다.

## Flow S1 — 파일 열기
1. C4 `list_data_files(root)` → selectbox
2. C4 `resolve_within(root, choice)`
3. C1 `sniff_format(path)` → 사이드바 기본값 (사용자가 덮어쓸 수 있음)
4. C1 `read_header(path, fmt)` → columns, data_start
5. C5 `get_job(path, mtime, size, fmt, data_start)` → C2 `IndexJob.start()` (캐시 히트면 기존 작업 재사용)

## Flow S2 — 페이지 표시 (첫 페이지는 인덱스 불필요)
1. page 0 → offset = data_start
2. page k → C2 `offset_of_row(k * page_size)`; None 이면 "인덱싱 중 (n행까지 확인)" 안내 + 이동 버튼 비활성
3. C1 `read_rows(path, fmt, offset, page_size)`
4. C3 `to_frame` → `infer_types` → `coerce` → `null_mask` 스타일 → `st.dataframe`
5. C3 `summarize` → 요약표 / 선택 컬럼 차트

## Flow S3 — 진행률 갱신
- `@st.fragment(run_every=0.5s)` 안에서 C2 `progress()` 만 읽어 진행 바·행 수 갱신. 완료되면 전체 페이지 수 확정, "끝" 버튼 활성화, fragment 갱신 중단 (전체 rerun 1회로 내비게이션 갱신).

## Flow S4 — 파일/포맷 변경
- 캐시 키(path, mtime, size, fmt, data_start)가 바뀌면 새 IndexJob. 이전 작업은 `stop()` (세션 상태에 이전 키 보관).
- 페이지 번호는 0 으로 리셋.

## Session State
| key | 의미 |
|---|---|
| `page` | 현재 페이지 번호 (0-based) |
| `page_size` | 50 / 100 / 500 |
| `job_key` | 현재 IndexJob 캐시 키 (변경 감지·이전 작업 중단용) |
