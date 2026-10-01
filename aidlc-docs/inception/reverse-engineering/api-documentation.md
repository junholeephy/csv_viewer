# API Documentation

## REST APIs
None.

## CLI
`python src/run.py [--data PATH] [--dry-run] [--limit N] [--rows N] [--seed N] [--adversarial] [--config PATH]`
- Exit codes: 0 OK, 1 schema mismatch, 2 could not start.
- stdout: RUN SUMMARY; stderr: progress.

## Internal APIs
### core.load
- `load_csv(path: str, limit: int = 0) -> list[dict]`
### core.schema
- `parse(value: str, dtype: str)`; `is_null(value) -> bool`; `validate(rows: list[dict]) -> Report`
### core.synth
- `generate(n=1000, seed=0, mode="normal"|"adversarial") -> list[dict]`
### core.pipeline
- `process_data(rows: list[dict]) -> dict` (raises `KeyError` on metric-name collision)
### core.report
- `render(*, version, args, source, n_rows, n_cols, violations, notes, metrics, runtime_s, status) -> str`
### Feature contract
- module attr `NAME: str`; `process_data(rows) -> dict` with keys prefixed by `NAME`.

## Data Models
### Field (frozen dataclass)
- **Fields**: name, dtype (int/float/str/datetime/category), nullable, allowed, rng, note, used.
### Report (frozen dataclass)
- **Fields**: violations: list[str], notes: list[str]; `ok` property.
