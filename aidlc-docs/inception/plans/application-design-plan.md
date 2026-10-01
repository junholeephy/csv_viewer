# Application Design Plan — csv-viewer

## Plan Checklist
- [x] 1. Analyze context (requirements.md, reverse-engineering artifacts)
- [x] 2. Collect answers to design questions below
- [x] 3. Analyze answers for ambiguity / contradictions
- [x] 4. Generate `components.md` (component definitions and responsibilities)
- [x] 5. Generate `component-methods.md` (method signatures; business rules deferred to Functional Design)
- [x] 6. Generate `services.md` (orchestration: file select → first page → background index → paging)
- [x] 7. Generate `component-dependency.md` (dependency matrix, data flow)
- [x] 8. Generate consolidated `application-design.md`
- [x] 9. Validate design completeness and consistency (vs FR-1..11, NFR-1..7, scaffold rules)

---

## Design Questions

각 `[Answer]:` 뒤에 문자를 적어주세요. 각 질문의 첫 번째 선택지가 추천안입니다(**추천** 표시). "추천대로"라고 답해도 됩니다.

## Question 1 — 페이지 리더(포맷 감지 / 오프셋 인덱스 / 페이지 읽기)를 어디에 두나
스캐폴드 원칙은 "포맷을 아는 코드는 `load.py` 한 곳"입니다.

A) **추천** — `src/core/load.py`를 확장한다. 기존 `load_csv` 옆에 `sniff_format`, `build_index`, `read_page`를 둔다. 원칙을 그대로 지키고, 파일이 하나라 포맷 버그를 고칠 곳도 하나입니다. 현재 18줄이라 늘어나도 부담이 없습니다.

B) `src/core/paged_csv.py` 모듈을 새로 만들고, `load.py` docstring에 "포맷 모듈은 둘"이라고 명시한다.

C) `src/core/viewer/reader.py`처럼 뷰어 패키지 안에 둔다. 응집도는 높지만, 배치 CLI가 나중에 같은 리더를 쓸 때 import 방향이 꼬입니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 2 — 백그라운드 인덱싱 메커니즘
Streamlit은 상호작용할 때마다 스크립트를 처음부터 다시 실행합니다. 그래서 인덱싱 작업이 재실행을 넘어 살아 있어야 합니다.

A) **추천** — `threading.Thread`를 소유한 `IndexJob` 객체를 `st.cache_resource`에 (경로, mtime, size, 인코딩, 구분자) 키로 둔다. UI는 `st.fragment(run_every=...)`로 진행률만 부분 갱신한다. 인덱싱은 I/O와 파싱 위주라 GIL 영향이 작고, 페이지 읽기는 다른 파일 핸들로 하므로 경합하지 않습니다.

B) 재실행마다 N MB씩 이어서 인덱싱한다(자동 새로고침 트리거). 스레드가 없어 단순하지만, 재실행이 멈추면 인덱싱도 멈추고 UI 반응이 끊깁니다.

C) `multiprocessing`/subprocess로 돌리고 결과를 파일로 공유한다. GIL을 완전히 회피하지만 과합니다(YAGNI). 디스크에 인덱스 파일도 남습니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 3 — 인덱스 세분도
A) **추천** — 50행마다 체크포인트 오프셋을 저장한다. 50은 선택 가능한 페이지 크기 50/100/500의 공약수라서, 모든 페이지 시작이 체크포인트와 정확히 일치합니다. 메모리는 행 단위 인덱스의 1/50입니다(1천만 행이면 약 1.6MB). 페이지를 읽을 때 체크포인트로 seek한 뒤 page_size행만 파싱합니다.

B) 모든 행의 오프셋을 저장한다(`array('q')`). 1천만 행이면 약 80MB입니다. 임의 행 단위 접근이 가능하지만, 현재 요구사항에는 필요 없습니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 4 — 뷰어 코드 구성
A) **추천** — `src/core/viewer/` 패키지로 나눈다.
- `jobs.py`: IndexJob, 스레드와 진행 상태
- `present.py`: 페이지 DataFrame 변환, 타입 추론, 요약, 스타일. Streamlit에 의존하지 않는 순수 함수라 테스트할 수 있습니다.
- `src/app.py`: Streamlit 위젯 배치만 담당

B) 리더를 뺀 나머지를 전부 `src/app.py` 한 파일에 둔다. 빠르지만 요약/타입 추론 로직을 Streamlit 없이 테스트하기 어렵습니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)

## Question 5 — 탐색 루트 디렉터리 지정
스캐폴드 규칙은 "바뀔 만한 값은 CLI 인자로"입니다.

A) **추천** — CLI 인자: `streamlit run src/app.py -- --root <dir>`. 기본값은 cwd입니다.

B) `configs/env.yaml`의 `paths.data_root`

C) A + B. CLI가 우선입니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천대로" 위임)
