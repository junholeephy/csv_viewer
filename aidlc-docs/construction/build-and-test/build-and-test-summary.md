# Build and Test Summary — csv-viewer

- **Build**: Python 3.14.7 venv, streamlit 1.64.0 / pandas 3.0.6 / hypothesis 6.168.3 설치 성공 (전부 wheel).
- **Unit + PBT**: 82 passed, 14 skipped (git 비저장소로 인한 기존 skip). PBT 결함 1건 발견·수정·회귀 고정.
- **Integration**: AppTest 4 시나리오 통과 + 샘플 데이터 수동 E2E 통과 (대용량, CP949, 열 불일치, 2백만 행 페이지 정확성).
- **Performance**: 1GB 기준 P-1/P-2/P-3 모두 충족.
- **Server**: `streamlit run src/app.py --server.address localhost -- --root <dir>` 기동, health ok.
- **Compliance**: `src/`·`TODO.md`·신규 테스트에 C9 어휘·개인 절대 경로·LLM import 없음. 배치 CLI 는 streamlit/pandas 없는 파이썬에서 `--dry-run` exit 0.

## PBT Compliance (Partial mode)
| Rule | Status | Evidence |
|---|---|---|
| PBT-02 Round-trip | Compliant | TP-2 `test_header_and_rows_round_trip` |
| PBT-03 Invariants | Compliant | TP-3, TP-4, TP-6, TP-7, TP-8 |
| PBT-07 Generators | Compliant | `tests/strategies.py` 도메인 전략(구분자·따옴표·CRLF·한글·cp949·빈 줄·ragged), 재사용 |
| PBT-08 Shrinking/Repro | Compliant | shrinking 기본값, print_blob, `ci` 프로파일(derandomize), `--hypothesis-seed` 안내. CI 파이프라인은 존재하지 않음(로컬 비 git 폴더) — 명령을 지침에 포함 |
| PBT-09 Framework | Compliant | hypothesis==6.168.3 in requirements-dev.txt, tech-stack-decisions.md |
| PBT-01, 04, 05, 06, 10 | Advisory | 01: Testable Properties 문서화 / 05: TP-1, TP-5 오라클 / 06: IndexJob 은 상태 PBT 대신 오라클(TP-5) — advisory / 10: 예제·PBT 파일 분리, PBT 회귀 예제 추가 |
