# Component Dependency — csv-viewer

## Dependency Matrix (row depends on column)
| | C1 load | C2 jobs | C3 present | C4 files | schema | streamlit | pandas |
|---|---|---|---|---|---|---|---|
| C1 load | - | | | | | | |
| C2 jobs | X | - | | | | | |
| C3 present | | | - | | X | | X |
| C4 files | | | | - | | | |
| C5 app | X | X | X | X | | X | X |

- 방향은 단방향: `app → viewer.* → load/schema`. `load` 와 `schema` 는 뷰어를 모른다.
- 기존 배치 경로(`run.py → core.__main__`)는 뷰어 모듈을 import 하지 않는다 → streamlit/pandas 가 없어도 배치 CLI 는 동작.

## Diagram

```mermaid
flowchart LR
    App["src/app.py (C5)"]
    Jobs["viewer/jobs.py (C2)"]
    Present["viewer/present.py (C3)"]
    Files["viewer/files.py (C4)"]
    Load["core/load.py (C1)"]
    Schema["core/schema.py"]
    Csv[("CSV file")]
    App --> Files
    App --> Load
    App --> Jobs
    App --> Present
    Jobs --> Load
    Present --> Schema
    Load --> Csv
```

Text alternative:
```
app -> files, load, jobs, present
jobs -> load
present -> schema
load -> CSV file (binary seek)
```

## Communication Patterns
- 모두 동일 프로세스 내 함수 호출.
- C2 ↔ C5: 공유 객체 + `threading.Lock` 보호 스냅샷(`progress()`), 폴링(fragment). 콜백·큐 없음.
- 파일 핸들: IndexJob 스레드와 페이지 읽기는 각자 별도 핸들을 연다 → seek 위치 경합 없음.

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as app
    participant L as load
    participant J as IndexJob
    participant P as present
    U->>A: select file
    A->>L: sniff_format, read_header
    A->>J: get_job then start
    J->>L: iter_row_offsets (background)
    A->>L: read_rows(data_start, page_size)
    A->>P: to_frame, infer_types, summarize
    A-->>U: first page
    U->>A: go to page k
    A->>J: offset_of_row(k * page_size)
    A->>L: read_rows(offset, page_size)
    A-->>U: page k
```
