# NFR Requirements Plan — csv-viewer

## Plan Checklist
- [x] 1. Analyze functional design (scanner, IndexJob, presenter, UI)
- [x] 2. Verify Python 3.14 wheel availability (dry-run `--only-binary :all:` on Python 3.14.7: streamlit 1.64.0, pandas 3.0.6, pyarrow 25.0.1, numpy 2.5.3, hypothesis 6.168.3, pytest 9.1.1 — 41 packages, all wheels OK)
- [x] 3. Collect answers to questions below
- [x] 4. Generate `nfr-requirements.md` (performance, scalability, availability, security, reliability, maintainability, usability)
- [x] 5. Generate `tech-stack-decisions.md` (incl. PBT framework per PBT-09)

---

## Questions
각 질문의 첫 번째 선택지가 추천안입니다.

## Question 1 — 의존성 고정 범위
A) **추천** — `requirements.txt`에는 직접 의존성(`streamlit==1.64.0`, `pandas==3.0.6`)만 정확한 버전으로 고정한다. 전이 의존성은 pip resolver에 맡깁니다. 운영 venv는 공용일 수 있어서(C7), 전이 의존성 41개를 모두 고정하면 남의 패키지와 충돌할 확률이 크게 올라갑니다.

B) 전이 의존성까지 41개를 전부 고정한다(완전 잠금). 재현성은 최고지만 공용 venv와의 충돌 위험이 큽니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천사항을 받아들일테니 끝까지 구현" 위임)

## Question 2 — 성능 목표와 측정 방식
요구사항 NFR-1(1GB 파일: 첫 페이지 1초 이내, 인덱스된 페이지 이동 300ms 이내)에 인덱싱 처리량 목표를 더합니다.

A) **추천** — 목표: 따옴표가 없는 파일은 인덱싱 ≥ 50MB/s(1GB를 20초 이내), 따옴표가 많은 파일은 ≥ 10MB/s. 측정은 개발 전용 벤치마크 스크립트 `tools/bench_viewer.py`로 합니다. 합성 CSV를 scratch에 생성해 측정하고, 이 스크립트는 이식에서 제외합니다(export-ignore). pytest에는 넣지 않습니다(느림).

B) 처리량 목표 없이 NFR-1만 수동으로 확인한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천사항을 받아들일테니 끝까지 구현" 위임)

## Question 3 — 접근 범위
A) **추천** — 로컬 전용. `--server.address localhost`로 실행하도록 안내하고 실행 스크립트에 넣는다. 인증은 없습니다(Security extension 끔). 실데이터를 다루므로 외부 바인딩은 막습니다.

B) 같은 네트워크의 다른 사람도 접속할 수 있게 한다(인증 없음).

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천사항을 받아들일테니 끝까지 구현" 위임)

## Question 4 — 관측성/로그
A) **추천** — UI 표시만 한다. 시작 실패(`--root` 오류)만 stderr로 내보냅니다. 셀 값이 들어간 로그는 없습니다(R-S1).

B) 파일 로그(`outputs/viewer.log`)에 이벤트(파일 열기, 인덱싱 시간)를 기록한다. 값은 기록하지 않습니다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A (추천안 — 사용자 "추천사항을 받아들일테니 끝까지 구현" 위임)
