# Code Quality Assessment

## Test Coverage
- **Overall**: Good for scaffold rules (no coverage tool configured)
- **Unit Tests**: Present for pipeline, schema, run entry
- **Integration Tests**: `test_spec_compliance.py` / `test_adopt.py` need a git repo (workspace is currently NOT a git repo, so archive-based tests skip)

## Code Quality Indicators
- **Linting**: Not configured
- **Code Style**: Consistent; type hints on public functions; Korean docstrings explaining rationale
- **Documentation**: Good (SCAFFOLD.md, TODO.md, IMPLEMENTATION_SPEC.md)

## Technical Debt
- `INPUT_SCHEMA` and `features/template` are placeholders.
- `load_csv` reads rows eagerly into memory (fine for `--limit`, not for paged viewing).

## Patterns and Anti-patterns
- **Good Patterns**: single format-aware module, schema-as-code, synthetic data instead of fixtures, graded exit codes, metric-collision guard.
- **Anti-patterns**: none significant.

## Fit Assessment for the Requested CSV Viewer (key finding)
- The scaffold's paradigm is a **headless batch CLI whose rule is "never print real data values"** (C3, spec "하지 말 것" #7). A Streamlit viewer's purpose is to **display real data values**. These conflict if the viewer is meant to run in the isolated operations environment.
- `.gitignore` blocks `*.csv`; the viewer must therefore use synthetic data (from `synth.py`) or user-chosen local files, never committed samples.
- Reusable pieces for the viewer: `load.py` (format isolation point), `schema.py` (`is_null`, dtype parsing), `synth.py` (demo/test data).
- Python 3.14 target: Streamlit / pandas / pyarrow wheel availability for 3.14 must be checked when pinning.
