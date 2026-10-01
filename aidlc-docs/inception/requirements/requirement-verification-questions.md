# Requirements Verification Questions

각 질문의 `[Answer]:` 뒤에 선택지 문자를 적어주세요. 맞는 선택지가 없으면 마지막 Other를 고르고 내용을 적으면 됩니다.
선택지마다 트레이드오프를 짧게 달아 두었습니다.

---

## Question 1 — 뷰어가 놓일 자리 (Reverse Engineering에서 발견한 핵심 충돌)
현재 스캐폴드는 "운영 환경으로 한 방향 이식 + 실데이터 값은 화면에 찍지 않음(C3)"을 전제로 합니다. CSV 뷰어는 실데이터 값을 보여주는 도구입니다. 뷰어를 어디서 어떻게 쓰나요?

A) 운영 환경으로 이식해서 실데이터를 보는 데 쓴다. C3는 "콘솔 리포트/반출물에 값을 남기지 않는다"로 좁혀 해석하고, 화면에서 보는 건 허용한다. 뷰어 코드는 `src/core` 안에 기능으로 넣는다.

B) 개발 장비 전용 도구로 둔다(합성 데이터나 로컬 파일 확인용). 이식에서 제외한다(`tools/viewer/` + export-ignore).

C) 스캐폴드 규칙과 무관한 독립 앱으로 본다. 이 저장소를 Streamlit 앱 프로젝트로 전환하고, 배치 CLI 부분은 그대로 두거나 정리한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (AI 추천 — 사용자 위임) — 화면 표시는 반출이 아니므로 C3와 양립. 뷰어는 src/core/viewer/ 패키지 + 별도 진입점 src/app.py. 포맷 처리는 load.py 계열에 둔다. RUN SUMMARY·로그에는 계속 값을 찍지 않는다.

## Question 2 — CSV 선택 방식
A) 서버(로컬) 파일 경로에서 고른다: 디렉터리 지정 → 파일 목록 selectbox. 파일을 디스크에서 직접 seek할 수 있어서 **진짜 지연 로딩**이 됩니다.

B) 브라우저 업로드(`st.file_uploader`). 사용은 편하지만 업로드할 때 파일 전체가 서버 메모리로 들어오고 기본 한도가 200MB입니다. 그래서 "전체를 읽지 않는다"는 이점이 렌더링 쪽으로 줄어듭니다.

C) 둘 다 지원한다(경로 방식이 기본이고, 업로드는 작은 파일용).

X) Other (please describe after [Answer]: tag below)

[Answer]: A (AI 추천 — 사용자 위임) — 루트 디렉터리 지정 후 파일 선택. 업로드는 YAGNI로 제외.

## Question 3 — 다룰 파일 크기
A) 대부분 수십 MB 이하

B) 수십 MB ~ 1GB

C) 1GB 이상, 수천만 행까지

X) Other (please describe after [Answer]: tag below)

[Answer]: B (AI 추천 — 사용자 위임) — 설계 기준 ~1GB. 오프셋 인덱스 구조라 그 이상도 동작은 하도록.

## Question 4 — 100행 단위 로딩 UX
A) 페이지네이션: 이전/다음 버튼과 페이지 번호 점프로 한 번에 100행만 표시합니다. 메모리가 일정하고 임의 위치로 바로 갈 수 있습니다.

B) "더 보기"(무한 스크롤 방식): 100행씩 뒤에 이어 붙입니다. 흐름은 자연스럽지만 오래 내리면 메모리와 렌더링 비용이 커집니다.

C) 둘 다(모드 전환)

X) Other (please describe after [Answer]: tag below)

[Answer]: A (AI 추천 — 사용자 위임)

## Question 5 — 페이지 크기
A) 100행 고정

B) 기본 100행, 사용자가 바꿀 수 있음(예: 50/100/500)

X) Other (please describe after [Answer]: tag below)

[Answer]: B (AI 추천 — 사용자 위임)

## Question 6 — 전체 행 수와 임의 페이지 이동
임의 페이지(예: 5,000번째 페이지)로 바로 가려면 행 시작 위치(바이트 오프셋) 인덱스가 필요합니다. 인덱스는 파일을 한 번 스캔해야 만들 수 있습니다.

A) 첫 페이지는 즉시 보여주고, 오프셋 인덱스는 백그라운드나 점진적으로 만든다. 완성되면 정확한 전체 행 수와 임의 점프를 제공한다.

B) 전체 행 수는 파일 크기로 추정만 하고, 순차 이동만 지원한다(인덱스 없음).

C) 파일을 열 때 인덱스를 미리 다 만든다. 구현은 가장 단순하지만 큰 파일이면 첫 화면이 늦게 뜹니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (AI 추천 — 사용자 위임)

## Question 7 — "가독성 높은 가시화"의 범위
A) 표 중심: 타입별 정렬과 숫자 포맷, 결측값 하이라이트, 컬럼 너비와 헤더 고정, 행 번호

B) A + 현재 로드된 페이지 기준의 컬럼 요약(타입, 결측 비율, min/max, 상위 값)과 간단한 차트

C) A + 파일 전체 기준의 컬럼 통계와 분포 차트. 전체 스캔이나 샘플링이 필요해서 비용이 큽니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: B (AI 추천 — 사용자 위임)

## Question 8 — 정렬/필터/검색
A) 필요 없음(보기 전용)

B) 현재 로드된 페이지 안에서만 정렬/필터

C) 파일 전체 대상 필터/검색. 스트리밍 스캔이 필요하고, 결과도 페이지 단위로 보여줍니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: B (AI 추천 — 사용자 위임) — st.dataframe 내장 컬럼 정렬 활용

## Question 9 — 읽기 엔진
A) 표준 `csv` + 바이트 오프셋 인덱스, 표시는 pandas DataFrame으로: seek로 정확히 100행만 읽고 의존성이 적습니다. 따옴표 안의 줄바꿈도 오프셋을 만들 때 csv 파서로 처리합니다.

B) pandas `read_csv(skiprows, nrows)` / chunksize: 구현은 쉽지만 뒤쪽 페이지일수록 앞부분을 다시 파싱해서 느려집니다(O(offset)).

C) polars `scan_csv` lazy + `slice`: 빠르지만 의존성이 크고 Python 3.14 wheel 확인이 필요합니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (AI 추천 — 사용자 위임)

## Question 10 — 인코딩/구분자
A) UTF-8(BOM 포함), 쉼표 구분만

B) 구분자 자동 감지(쉼표/탭/세미콜론/파이프) + 인코딩 선택(UTF-8, CP949/EUC-KR)

X) Other (please describe after [Answer]: tag below)

[Answer]: B (AI 추천 — 사용자 위임)

## Question 11 — Python 버전 타깃
명세는 3.14를 요구하고, 이 장비는 3.13.1입니다.

A) 3.14 기준으로 고정한다(로컬에 3.14 venv를 새로 만든다). Streamlit/pandas 버전도 3.14 wheel이 있는 것으로 고정합니다.

B) 지금은 3.13으로 프로토타이핑하고, 이식할 때 3.14로 검증한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (AI 추천 — 사용자 위임) — 로컬에 /opt/homebrew/bin/python3.14 확인됨

## Question 12 — 완성도 수준
A) 프로토타입: 빠르게 동작하는 앱을 먼저 만들고, 로더 핵심 로직(오프셋 인덱스, 페이지 읽기)에만 단위 테스트를 단다.

B) 재사용 코드 수준: 타입힌트를 쓰고, 로더와 요약 로직 전반에 테스트를 단다. UI는 수동 검증합니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (AI 추천 — 사용자 위임) — 사용자 전역 작업 스타일(탐색 단계는 빠르게)과 일치

---

## Question 13 — Security Extension
이 프로젝트에 security extension 규칙을 강제할까요?

A) Yes — 모든 SECURITY 규칙을 차단 조건으로 강제한다(프로덕션급 애플리케이션에 권장)

B) No — SECURITY 규칙을 모두 건너뛴다(PoC, 프로토타입, 실험 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: B (AI 추천 — 사용자 위임) — 로컬 단일 사용자 도구. 단, 파일 선택은 지정 루트 하위로 제한

## Question 14 — Resiliency Extension
이 프로젝트에 resiliency baseline을 적용할까요?

**이 확장이 하는 일:** AWS Well-Architected Framework(Reliability Pillar)에서 가져온 **설계 단계의 방향성 모범 사례**를 적용합니다. 요구사항, 설계, 코드를 내결함성·고가용성·관측성·복구 가능성 쪽으로 이끕니다. 비즈니스 목표, 변경 관리, 관측성, 고가용성, 재해 복구, 지속 개선에 걸친 15개 영역을 다룹니다.

**이 확장이 하지 않는 일:** 적용해도 워크로드가 프로덕션 준비 상태가 되지 않습니다. 가용성·RTO·RPO 목표를 인증하거나 보장하지도 않습니다. 좋은 결정을 일찍 잡아주는 **출발점**일 뿐이고, 완성된 시스템에 대한 공식 **AWS Well-Architected Review**를 대신하지 않습니다.

A) Yes — resiliency baseline을 방향성 모범 사례와 설계 가이드로 적용한다(비즈니스 핵심 워크로드에 권장. 출시 전에 검증하고 보강할 출발점으로 씁니다)

B) No — resiliency baseline을 건너뛴다(빠른 반복이 신뢰성보다 중요한 PoC, 프로토타입, 실험 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: B (AI 추천 — 사용자 위임)

## Question 15 — Property-Based Testing Extension
이 프로젝트에 property-based testing(PBT) 규칙을 강제할까요?

A) Yes — 모든 PBT 규칙을 차단 조건으로 강제한다(비즈니스 로직, 데이터 변환, 직렬화, 상태 있는 컴포넌트가 있는 프로젝트에 권장)

B) Partial — 순수 함수와 직렬화 왕복에만 PBT 규칙을 강제한다. 이 프로젝트라면 "오프셋 인덱스로 읽은 N번째 페이지 == 순차 파싱한 N번째 100행" 같은 성질이 좋은 대상입니다.

C) No — PBT 규칙을 모두 건너뛴다(단순 CRUD, UI 전용, 비즈니스 로직이 거의 없는 얇은 통합 계층에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: B (AI 추천 — 사용자 위임) — 오프셋 인덱스/페이지 읽기 순수 함수에 한정
