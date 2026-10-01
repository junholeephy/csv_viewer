# Integration Test Instructions

## Automated (Streamlit AppTest, no browser) — `tests/test_app.py`
1. 랜딩: 파일 미선택 안내
2. 파일 선택 → 첫 페이지 100행(행 번호 1부터) → 인덱싱 완료 후 "전체 250행 · 3페이지" → 다음 → 101행부터 → 끝 → 50행
3. 페이지 크기 100→50 변경 시 같은 첫 행(101) 유지
4. 빈 파일 / 헤더만 있는 파일에서 예외 없음

## Manual end-to-end (performed 2026-10-01 with scratchpad sample data, outside the repo)
| Scenario | Result |
|---|---|
| 105.8MB, 2,000,000행, 따옴표 안 줄바꿈 20,618개 — 첫 페이지 | 0.47s (AppTest 오버헤드 포함), 예외 없음 |
| 15,000번째 / 20,000번째 페이지 | 첫 행 order_id 1499901 / 1999901 — 행 번호와 일치 (따옴표 안 줄바꿈이 행 수를 흐리지 않음) |
| 요약 타입 추론 | int/str/float/int/str/datetime/bool/str — 기대대로 |
| CP949 + 세미콜론 파일 | 인코딩 `cp949`, 구분자 `;` 자동 감지, 한글 헤더 정상 |
| 열 수 불일치 TSV | 경고 "2개", `⚠`·`…extra` 열 표시 |
| 실서버 | `streamlit run ... --server.address localhost` → `/_stcore/health` = ok |

## Browser checklist (사람이 확인)
- 진행 바가 0.5초마다 갱신되고 완료 시 사라지며 "끝" 버튼 활성화
- 결측 셀 주황 배경(라이트/다크), 숫자 우측 정렬·천 단위 구분, 헤더 클릭 정렬
- 아직 인덱싱 안 된 페이지로 "다음" → 토스트 안내
