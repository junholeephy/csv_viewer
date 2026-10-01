# Requirements — Streamlit CSV Viewer

## Intent Analysis
- **User Request**: "streamlit으로 csv를 선택하고, 이를 가독성 높게 가시화. 모든 데이터를 한꺼번에 로딩하지 않고 100라인 단위로 동적으로 로딩해서 지연시간을 줄이기"
- **Request Type**: New Feature (기존 배치 CLI 스캐폴드 위에 대화형 뷰어 추가)
- **Scope Estimate**: Multiple Components (`load` 계열 확장 + 새 `viewer` 패키지 + 새 진입점 + 의존성)
- **Complexity Estimate**: Moderate (핵심 난점은 오프셋 인덱스와 Streamlit 재실행 모델에서의 백그라운드 인덱싱)
- **Depth**: Standard
- **Answer Source**: 사용자가 "추천대로" 위임 → 모든 답은 AI 추천값 (`requirement-verification-questions.md` 참조)

## Key Decisions (from answers)
| Q | 결정 | 근거 |
|---|---|---|
| Q1 | 운영 환경으로 이식되는 정식 기능. `src/core/viewer/` + 진입점 `src/app.py` | 화면 표시는 반출이 아니므로 C3와 양립. RUN SUMMARY·로그에는 여전히 값을 찍지 않는다 |
| Q2 | 지정 루트 디렉터리 하위 파일 선택 (업로드 미지원) | 디스크 seek 가능해야 진짜 지연 로딩 |
| Q3 | 설계 기준 ~1GB, 그 이상도 동작 | |
| Q4/Q5 | 페이지네이션, 기본 100행 (50/100/500 선택) | 메모리 일정, 임의 위치 이동 |
| Q6 | 첫 페이지 즉시 표시 + 오프셋 인덱스 백그라운드 구축 | 첫 화면 지연과 임의 점프 둘 다 확보 |
| Q7 | 표 가독성 + 현재 페이지 기준 컬럼 요약/차트 | 전체 스캔 비용 회피 |
| Q8 | 현재 페이지 내 정렬만 (st.dataframe 내장) | |
| Q9 | stdlib `csv` + 바이트 오프셋 인덱스, 표시는 pandas | pandas skiprows 는 O(offset) |
| Q10 | 구분자 자동 감지 + 인코딩 선택(UTF-8/UTF-8-BOM/CP949) | 국내 CSV 는 CP949 빈번 |
| Q11 | Python 3.14 고정 | 명세 C7, 로컬에 3.14 존재 |
| Q12 | 프로토타입 수준, 로더 핵심에만 테스트 | 사용자 작업 스타일 |
| Q13–15 | Security: No / Resiliency: No / PBT: Partial | |

## Functional Requirements
- **FR-1 파일 선택**: 루트 디렉터리(CLI 인자 `--root`, 기본 cwd) 하위의 `*.csv`/`*.tsv`/`*.txt` 를 재귀 목록으로 보여주고 selectbox 로 선택한다. 루트 밖 경로는 선택할 수 없다.
- **FR-2 포맷 감지**: 파일 앞부분 샘플로 구분자(`,` `\t` `;` `|`)를 자동 감지하고, 인코딩 기본값은 UTF-8-BOM 허용이며 사이드바에서 CP949 등으로 바꿀 수 있다. 감지 결과는 사이드바에서 수동 수정 가능.
- **FR-3 첫 페이지 즉시 표시**: 파일 선택 후 인덱스 완성을 기다리지 않고 헤더 + 첫 페이지를 표시한다.
- **FR-4 페이지 읽기**: 페이지 N 요청 시 해당 행 시작 바이트 오프셋으로 seek 해서 page_size 행만 파싱한다. 따옴표 안 줄바꿈이 있어도 행 경계가 정확해야 한다.
- **FR-5 백그라운드 인덱싱**: 오프셋 인덱스를 백그라운드에서 구축하고, 진행률(바이트 기준)과 지금까지 확인된 행 수를 표시한다. 완료되면 정확한 전체 행 수/페이지 수를 표시한다.
- **FR-6 페이지 이동**: 처음/이전/다음/끝, 페이지 번호 입력. 아직 인덱싱되지 않은 페이지로의 점프는 인덱스가 그 지점에 도달할 때까지 대기(진행 표시)하거나 안내한다. "끝"은 인덱스 완료 후 활성화.
- **FR-7 표 가독성**: 원본 행 번호 표시, 헤더 고정, 숫자 컬럼 우측 정렬·천 단위 구분, 결측값(`schema.NULL_TOKENS` 기준) 하이라이트, 긴 텍스트 컬럼 폭 제한.
- **FR-8 컬럼 타입 추론**: 현재 페이지 값으로 int/float/datetime/bool/str 추론 (페이지 기준임을 UI에 명시).
- **FR-9 페이지 요약**: 컬럼별 타입, 결측 비율, 숫자형 min/max/mean, 범주형 상위 값 빈도를 표로 표시. 선택한 컬럼에 대해 간단한 차트(숫자형 히스토그램, 범주형 막대).
- **FR-10 페이지 내 정렬**: 표 컬럼 헤더 클릭 정렬 (현재 페이지 한정).
- **FR-11 오류 표시**: 인코딩 오류, 열 수 불일치 행, 빈 파일, 헤더만 있는 파일을 앱이 죽지 않고 화면에 안내한다.

## Non-Functional Requirements
- **NFR-1 지연**: 1GB 파일에서 파일 선택 → 첫 페이지 표시 1초 이내 (로컬 SSD 기준). 인덱스된 임의 페이지 이동 300ms 이내.
- **NFR-2 메모리**: 파일 크기와 무관하게 표시 데이터는 한 페이지분. 오프셋 인덱스는 행당 8바이트 수준(예: 1천만 행 ≈ 80MB) — 필요 시 page_size 간격 체크포인트로 축소.
- **NFR-3 재실행 모델 대응**: Streamlit 재실행마다 파일을 다시 스캔하지 않는다. 인덱스는 (경로, mtime, size, 인코딩, 구분자) 키로 프로세스 캐시에 보관하고, 파일이 바뀌면 무효화한다.
- **NFR-4 스캐폴드 규칙 준수**: `src/` 안에 LLM/외부 API import 금지, 데이터 파일 커밋 금지(데모는 `synth.py` 로 생성), 개인 절대 경로 금지, 워크플로 어휘(C9) 금지, `requirements.txt` 버전 고정.
- **NFR-5 런타임**: Python 3.14. streamlit, pandas(및 필요 시 그 의존성)를 3.14 wheel 이 있는 버전으로 고정. 개발 전용(hypothesis)은 `requirements-dev.txt`.
- **NFR-6 기존 동작 보존**: 기존 배치 CLI(`src/run.py`)와 기존 테스트는 그대로 통과해야 한다.
- **NFR-7 테스트**: 오프셋 인덱싱/페이지 읽기/구분자 감지에 단위 테스트 + PBT(Partial: PBT-02, 03, 07, 08, 09 강제). UI 는 수동 검증.

## Technical Context
- 포맷 지식은 load 계열 한 곳에 둔다는 스캐폴드 원칙을 유지: 오프셋 인덱스·페이지 리더는 `src/core/` 의 로더 모듈에 둔다(정확한 위치는 Application Design 에서 확정).
- 진입점: `streamlit run src/app.py -- --root <dir>`. `run.py` 의 venv 전환은 Streamlit 경로에 적용되지 않으므로 실행 venv 를 직접 활성화해야 한다 → `TODO.md` 에 항목 추가.
- 바이트 오프셋은 텍스트 모드가 아닌 바이너리 모드 기준이어야 한다(텍스트 모드 `tell()` 은 불투명 쿠키). 따옴표 안 줄바꿈 처리를 위해 인덱서는 따옴표 상태를 추적한다.

## Out of Scope
- 브라우저 업로드, 파일 전체 대상 필터/검색/통계, 편집/저장, 다중 사용자/인증, Excel/Parquet.

## Extension Configuration
- Security Baseline: **No**
- Resiliency Baseline: **No**
- Property-Based Testing: **Partial** (PBT-02, 03, 07, 08, 09 blocking; 나머지 advisory)
