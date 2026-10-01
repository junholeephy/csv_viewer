# Build Instructions

## Prerequisites
- Python 3.14 (verified 3.14.7), pip, venv. macOS / Linux.
- Runtime deps: `requirements.txt` (streamlit 1.64.0, pandas 3.0.6). Dev: `requirements-dev.txt` (pytest 9.1.1, hypothesis 6.168.3).

## Steps
```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest==9.1.1 hypothesis==6.168.3   # 개발용 (anthropic 은 뷰어에 불필요)
```
No compile step. Build verified by import: `.venv/bin/python -c "import streamlit, pandas"`.

## Run
```bash
.venv/bin/streamlit run src/app.py --server.address localhost -- --root <data-dir>
# → http://localhost:8501
```

## Troubleshooting
- `ModuleNotFoundError: streamlit` → 다른 venv 로 실행됨. `src/run.py` 의 venv 전환은 streamlit 경로에 적용되지 않으므로 직접 활성화.
- "For better performance, install the Watchdog module" → 무시 가능 (파일 변경 감지 성능 안내).
