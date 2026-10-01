# Unit Test Execution

```bash
.venv/bin/python -m pytest -q                          # 전체
.venv/bin/python -m pytest -q tests/test_*pbt.py --hypothesis-show-statistics
HYPOTHESIS_PROFILE=ci .venv/bin/python -m pytest -q   # 결정적 실행 (derandomize)
.venv/bin/python -m pytest -q --hypothesis-seed=1234  # 특정 seed 재현
```

## Last result (2026-10-01)
- **82 passed, 14 skipped** (2.8s). 스킵 14개는 기존 `test_spec_compliance.py`/`test_adopt.py` 의 git 저장소 의존 테스트 — 이 작업 폴더가 git 저장소가 아니어서 skip (기존 동작).
- PBT: 각 성질 100 examples, 실패 시 `@reproduce_failure` blob 출력 (print_blob=True). Shrinking 기본값 유지.
- PBT 가 찾은 결함 1건(헤더만 있는 파일의 0행 오프셋)을 수정하고 예제 회귀 테스트로 고정.
