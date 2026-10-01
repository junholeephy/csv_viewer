# NFR Requirements — csv-viewer

## Performance
| ID | Target | Measure |
|---|---|---|
| P-1 | 1GB 파일 선택 → 첫 페이지 데이터 준비 ≤ 1s (sniff + header + read_rows) | `tools/bench_viewer.py` |
| P-2 | 인덱스된 임의 페이지 `read_rows` ≤ 300ms (page_size 500 기준) | bench |
| P-3 | 인덱싱 처리량: 따옴표 없는 파일 ≥ 50MB/s, 따옴표 많은 파일 ≥ 10MB/s | bench |
| P-4 | 진행률 fragment 갱신 0.5s 주기, 페이지 이동 시 전체 rerun 1회 | 수동 |

## Scalability / Capacity
- 단일 사용자, 단일 프로세스. 파일 크기 설계 기준 1GB, 그 이상은 인덱싱 시간만 선형 증가.
- 메모리: 체크포인트 8B × rows/50 + 한 페이지. 동시에 여러 파일을 열면 파일별 IndexJob 이 캐시에 남음 → 캐시 `max_entries=4`.

## Availability / Reliability
- 로컬 도구. 가용성 목표 없음. 오류는 UI 에 표시하고 앱은 계속 동작 (business-rules 오류 표).
- 인덱싱 스레드는 daemon. 파일 변경/선택 변경 시 협조적 중단.

## Security
- Security extension: 비활성. 최소 조치: `--server.address localhost` 바인딩, 파일 선택은 `--root` 하위로 제한(R-F2), 셀 값 로그 금지(R-S1).

## Observability
- UI 표시만. 시작 실패만 stderr.

## Maintainability
- Streamlit 의존은 `src/app.py` 에만. C1–C4 는 타입힌트 + pytest.
- 프로토타입 수준: 로더 핵심에 예제 테스트 + PBT(Partial), presenter/files 에 예제 테스트 + PBT 일부.

## Usability
- Streamlit 기본 테마(라이트/다크) 모두에서 결측 하이라이트 식별 가능한 반투명 색.
- 모든 요약/차트에 "현재 페이지 기준" 캡션.

## Compatibility
- Python 3.14 (검증: 3.14.7). 기존 배치 CLI 는 streamlit/pandas 없이도 동작 (뷰어 모듈 미 import).
