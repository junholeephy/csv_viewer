# Component Methods — csv-viewer

비즈니스 규칙(따옴표 상태 기계, 타입 추론 규칙 등)의 상세는 Functional Design 에서 정의한다.

## C1 `core/load.py`
```python
@dataclass(frozen=True)
class CsvFormat:
    encoding: str            # "utf-8-sig" | "cp949" | ...
    delimiter: str           # "," "\t" ";" "|"
    quotechar: str = '"'

def sniff_format(path: str, encoding: str | None = None, sample_bytes: int = 64_000) -> CsvFormat
    # 앞부분 샘플로 구분자 감지. encoding None 이면 utf-8-sig 시도 후 실패 시 cp949.

def read_header(path: str, fmt: CsvFormat) -> tuple[list[str], int]
    # (컬럼 이름, 첫 데이터 행의 바이트 오프셋)

def iter_row_offsets(path: str, fmt: CsvFormat, start: int) -> Iterator[int]
    # start 부터 각 데이터 행의 시작 바이트 오프셋을 순서대로 yield (따옴표 안 줄바꿈 무시).

def read_rows(path: str, fmt: CsvFormat, offset: int, n: int) -> list[list[str]]
    # offset 으로 seek 해서 최대 n 행을 파싱해 반환.
```

## C2 `core/viewer/jobs.py`
```python
@dataclass(frozen=True)
class IndexProgress:
    rows_seen: int
    bytes_done: int
    total_bytes: int
    done: bool
    error: str | None

class IndexJob:
    def __init__(self, path: str, fmt: CsvFormat, data_start: int, stride: int = 50) -> None
    def start(self) -> None                       # 데몬 스레드 시작 (멱등)
    def stop(self) -> None                        # 협조적 중단
    def progress(self) -> IndexProgress           # 스냅샷 (lock 보호)
    def offset_of_row(self, row: int) -> int | None
        # row 는 stride 의 배수. 아직 인덱싱 전이면 None.
```

## C3 `core/viewer/present.py`
```python
def to_frame(rows: list[list[str]], columns: list[str], first_row: int) -> pd.DataFrame
    # 인덱스 = 원본 데이터 행 번호(1-based). 열 수 불일치 행은 패딩/절단 + 표시.
def infer_types(df: pd.DataFrame) -> dict[str, str]     # "int"|"float"|"datetime"|"bool"|"str"
def coerce(df: pd.DataFrame, types: dict[str, str]) -> pd.DataFrame
def null_mask(df: pd.DataFrame) -> pd.DataFrame          # schema.is_null 기준
def summarize(df: pd.DataFrame, types: dict[str, str]) -> pd.DataFrame
    # 컬럼별 type, null %, min, max, mean, top values
```

## C4 `core/viewer/files.py`
```python
def list_data_files(root: Path, patterns=("*.csv", "*.tsv", "*.txt")) -> list[str]
def resolve_within(root: Path, rel: str) -> Path        # 루트 밖이면 ValueError
```

## C5 `src/app.py`
```python
def parse_args(argv: list[str]) -> argparse.Namespace   # --root
@st.cache_resource
def get_job(path: str, mtime: float, size: int, fmt: CsvFormat, data_start: int) -> IndexJob
def main() -> None
```
