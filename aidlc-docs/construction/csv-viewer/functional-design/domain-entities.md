# Domain Entities — csv-viewer

| Entity | Fields | Owner | Notes |
|---|---|---|---|
| `CsvFormat` | `encoding: str`, `delimiter: str` (1 ASCII byte), `quotechar: str = '"'` | C1 | frozen. 캐시 키의 일부 |
| `Header` | `columns: list[str]` (정규화 후), `header_offset: int`, `data_start: int` | C1 `read_header` 반환 (tuple) | `data_start` = 첫 데이터 행의 바이트 오프셋. 데이터가 없으면 파일 크기 |
| Row offset | `int` (바이트, 파일 시작 기준, BOM 포함) | C1 `iter_row_offsets` | 비어 있지 않은 데이터 행만 |
| Checkpoint index | `list[int]`, `checkpoints[i]` = 데이터 행 `i*stride` 의 오프셋, `stride = 50` | C2 | `checkpoints[0] = data_start` |
| `IndexProgress` | `rows_seen`, `bytes_done`, `total_bytes`, `done`, `error` | C2 | lock 하에 만든 불변 스냅샷 |
| Page | `number` (0-based), `size` ∈ {50,100,500}, `first_row = number*size` (0-based 데이터 행), `rows: list[list[str]]` | C5/C1 | 표시용 행 번호는 `first_row + 1` 부터 (1-based) |
| `PageFrame` | pandas DataFrame, index = 1-based 원본 데이터 행 번호, 컬럼 = 헤더 (+ `…extra`, `⚠`) | C3 | 원본 문자열 보관(raw)과 변환본(coerced) 두 벌 |
| `ColumnType` | `"int" \| "float" \| "bool" \| "datetime" \| "str" \| "empty"` | C3 | 페이지 기준 |
| `ColumnSummary` | `column, type, non_null, null_pct, min, max, mean, unique, top, note` | C3 `summarize` 의 한 행 | `note` 예: "숫자처럼 보이지만 3개 실패" |
| `PageWarnings` | `ragged_rows: int`, `decode_errors: int` | C3/C5 | 페이지 상단 경고 |

## Relationships
```
CsvFormat 1 --- 1 Header           (같은 파일, 같은 포맷)
CsvFormat + Header 1 --- 1 IndexJob --- * checkpoints
Page --(first_row % stride == 0)--> checkpoint lookup --> offset --> rows --> PageFrame --> ColumnSummary*
```
