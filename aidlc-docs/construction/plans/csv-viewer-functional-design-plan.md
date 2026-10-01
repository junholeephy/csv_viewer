# Functional Design Plan — csv-viewer

## Plan Checklist
- [x] 1. Analyze unit context (single unit; application-design artifacts as unit definition)
- [x] 2. Collect answers to questions below
- [x] 3. Analyze answers for ambiguity
- [x] 4. Generate `domain-entities.md` (CsvFormat, Header, Checkpoint index, Page, IndexProgress, ColumnType, ColumnSummary)
- [x] 5. Generate `business-logic-model.md` (quote-aware offset scan, page→offset mapping, sniffing, type inference, summary)
- [x] 6. Generate `business-rules.md` (validation, edge cases, error handling)
- [x] 7. Generate `frontend-components.md` (Streamlit layout, state, interactions)
- [x] 8. Include "Testable Properties" section (PBT-01, advisory in Partial mode, feeds PBT-02/03)

---

## Questions
각 질문의 첫 번째 선택지가 추천안입니다. "추천대로"라고 답해도 됩니다.

## Question 1 — 지원할 CSV 방언(줄바꿈/따옴표)
A) **추천** — RFC 4180 기준. 행 종결자는 LF와 CRLF입니다. 따옴표 안의 `""`는 이스케이프된 따옴표로 보고, 따옴표 안의 줄바꿈과 구분자는 데이터로 취급합니다. 단독 CR(구형 Mac) 종결자는 지원하지 않습니다.

B) A + 단독 CR까지 지원. 스캐너 상태가 하나 늘고, CRLF와 구분하는 로직이 필요합니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 2 — 빈 줄 처리
A) **추천** — 완전히 빈 줄은 데이터 행으로 세지 않는다. 인덱서와 리더가 같은 규칙을 써서 행 번호가 일치하도록 합니다(`csv.reader`는 빈 줄을 `[]`로 돌려주므로 리더 쪽에서 건너뜁니다).

B) 빈 줄도 한 행(모든 값이 결측)으로 센다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 3 — 열 수가 헤더와 다른 행(ragged row)
A) **추천** — 모자라면 결측으로 채우고, 넘치면 넘친 값을 `…extra` 컬럼 하나에 이어 붙인다. 해당 행은 표시하고 요약에 "불일치 행 n개"로 집계합니다. 앱은 계속 동작합니다.

B) 넘친 값은 버리고 모자라면 채운다. 표시는 하지 않습니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 4 — 헤더
A) **추천** — 첫 행은 항상 헤더로 본다. 빈 이름은 `col_<n>`으로 바꾸고, 중복 이름은 `name`, `name.1`, `name.2`처럼 번호를 붙여 구분합니다.

B) 헤더 유무를 자동 감지하는 토글을 둔다(`csv.Sniffer.has_header`). 추측이 틀리는 경우가 꽤 있습니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 5 — 페이지 기준 타입 추론 규칙
A) **추천** — 결측이 아닌 값이 **전부** 해석될 때만 그 타입으로 본다. 판정 순서는 int → float → bool → datetime(ISO 8601) → str입니다. 하나라도 실패하면 str로 두고, 요약에 "숫자처럼 보이지만 n개 실패"로 표시합니다. 엄격하게 판정하므로 표가 값을 조용히 바꾸는 일이 없습니다.

B) 95% 이상 해석되면 그 타입으로 보고, 실패한 값은 결측으로 표시한다. 더 관대하지만 원본 값을 숨깁니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 6 — 숫자 표시 형식
A) **추천** — int는 천 단위 구분(1,234,567)으로 보여준다. float은 천 단위 구분에 소수점 이하를 최대 4자리까지만 표시하고 끝의 0은 제거합니다. 원본 문자열은 셀 툴팁 대신 "원본 보기" 토글로 볼 수 있습니다.

B) 원본 문자열을 그대로 표시하고 우측 정렬만 한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 7 — 인코딩 오류(파일 중간의 잘못된 바이트)
A) **추천** — 해당 바이트를 대체 문자(U+FFFD)로 바꿔 표시하고, 페이지 상단에 "디코딩 오류 n건, 인코딩 변경을 고려하세요"라고 경고한다. 인덱서는 바이트 단위로 동작하므로 인코딩 오류의 영향을 받지 않습니다.

B) 오류를 내고 해당 페이지를 표시하지 않는다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 8 — 아직 인덱싱되지 않은 페이지로 점프할 때
A) **추천** — 페이지 번호 입력의 최댓값을 "현재 인덱싱된 마지막 페이지"로 제한하고 "인덱싱 진행 중: n행까지 확인"을 표시한다. 다음 페이지 버튼은 그 페이지의 체크포인트가 생기면 활성화합니다.

B) 입력을 허용하되, 해당 지점이 인덱싱될 때까지 스피너를 띄우고 기다린다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)
