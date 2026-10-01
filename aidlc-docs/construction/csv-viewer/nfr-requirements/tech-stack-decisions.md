# Tech Stack Decisions — csv-viewer

| 영역 | 선택 | 버전 | 근거 |
|---|---|---|---|
| Runtime | CPython | 3.14 (3.14.7 검증) | 명세 C7 |
| UI | streamlit | ==1.64.0 | 요구사항. `st.fragment(run_every)`, `st.cache_resource` 사용. 3.14 wheel 확인 |
| DataFrame | pandas | ==3.0.6 | 표 표시/요약. 3.14 wheel 확인. 전이 의존(numpy 2.5.3, pyarrow 25.0.1)은 resolver 에 맡김 |
| CSV 파싱 | stdlib `csv` + 자체 바이트 스캐너 | - | 오프셋 seek 정확성. pandas `skiprows` 는 O(offset) |
| 동시성 | stdlib `threading` | - | 인덱싱은 I/O+바이트 탐색 위주 |
| Test runner | pytest | ==9.1.1 (기존) | 기존 |
| **PBT framework (PBT-09)** | **hypothesis** | ==6.168.3 | Python 표준 PBT. 커스텀 전략(`csv_tables`), 자동 shrinking, `--hypothesis-seed` 재현, pytest 통합 |
| Bench | stdlib (`time.perf_counter`) | - | `tools/bench_viewer.py`, export-ignore |

## Pinning
- `requirements.txt`: 직접 의존성만 `==` 고정 (streamlit, pandas). 공용 venv 충돌 최소화.
- `requirements-dev.txt`: pytest, hypothesis 추가 (anthropic 기존 유지).

## PBT reproducibility (PBT-08)
- Hypothesis 기본 shrinking 유지(비활성화 금지).
- `tests/conftest.py` 에서 프로파일 등록: `default`(print_blob=True), `ci`(derandomize=True). 실패 시 재현 blob 출력, `pytest --hypothesis-seed=<n>` 로 재현.
- CI 없음(로컬 저장소, git 아님) — Build and Test 지침에 seed 로깅 명령 포함.
