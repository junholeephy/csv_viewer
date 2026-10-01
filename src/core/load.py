"""입력 적재.

포맷을 아는 코드는 여기에만 둔다. 처리 로직은 dict 의 리스트만 본다 —
실제 데이터의 형식이 예상과 다를 때 고칠 곳이 이 파일 하나여야 하기 때문이다.

뷰어용 페이지 읽기도 같은 이유로 여기 있다. 파일 전체를 읽지 않고, 행이 시작하는
바이트 위치(오프셋)로 바로 건너뛰어 필요한 행만 파싱한다.
"""

import codecs
import csv
import io
import os
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass

# 긴 텍스트 필드에서 csv 모듈 기본 한도(128KB)에 걸려 페이지 하나가 통째로 죽지 않도록
csv.field_size_limit(2**31 - 1)


def load_csv(path: str, limit: int = 0) -> list[dict]:
    """앞 limit 행만 읽는다 (0 = 전체). BOM 이 붙은 파일도 그대로 연다."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = []
        for i, row in enumerate(csv.DictReader(fh)):
            if limit and i >= limit:
                break
            rows.append(row)
    return rows


# ── 페이지 단위 읽기 ────────────────────────────────────────────────────────

DELIMITERS = (",", "\t", ";", "|")
ENCODINGS = ("utf-8-sig", "cp949", "euc-kr", "latin-1")

_CHUNK = 1 << 20
_BOM = codecs.BOM_UTF8

# 행 경계 스캐너의 상태. csv 모듈 기본 방언(doublequote=True, strict=False)과 같은 경계를 낸다
_START, _FIELD, _QUOTED, _QUOTE_IN_QUOTED = range(4)


@dataclass(frozen=True)
class CsvFormat:
    encoding: str
    delimiter: str
    quotechar: str = '"'


def _is_utf8(encoding: str) -> bool:
    return encoding.lower().replace("_", "-") in ("utf-8", "utf8", "utf-8-sig")


def _bom_len(path: str, fmt: CsvFormat) -> int:
    if not _is_utf8(fmt.encoding):
        return 0
    with open(path, "rb") as fh:
        return len(_BOM) if fh.read(len(_BOM)) == _BOM else 0


def _decodes(sample: bytes, encoding: str, final: bool) -> bool:
    try:
        codecs.getincrementaldecoder(encoding)().decode(sample, final=final)
        return True
    except UnicodeDecodeError:
        return False


def sniff_format(path: str, encoding: str | None = None,
                 sample_bytes: int = 64_000) -> CsvFormat:
    """앞부분 샘플로 인코딩(지정 안 했을 때)과 구분자를 고른다.

    구분자는 후보마다 행별 필드 수를 세어, 필드가 둘 이상이면서 행마다 가장 일정한
    것을 고른다. 단일 컬럼 파일처럼 판단할 근거가 없으면 쉼표(.tsv 는 탭)다.
    """
    with open(path, "rb") as fh:
        sample = fh.read(sample_bytes)
    truncated = len(sample) == sample_bytes

    if encoding is None:
        encoding = next((e for e in ENCODINGS[:2] if _decodes(sample, e, not truncated)),
                        "latin-1")

    text = codecs.getincrementaldecoder(encoding)(errors="replace").decode(
        sample, final=not truncated)
    if truncated and "\n" in text:
        text = text[: text.rindex("\n")]          # 잘린 마지막 행은 판단에서 뺀다

    prefer = "\t" if path.lower().endswith(".tsv") else ","
    order = (prefer, *(d for d in DELIMITERS if d != prefer))
    best: tuple[tuple[float, int], str] | None = None
    for delim in order:
        try:
            counts = [len(r) for r in csv.reader(io.StringIO(text), delimiter=delim) if r][:50]
        except csv.Error:
            continue
        if not counts:
            continue
        mode = Counter(counts).most_common(1)[0][0]
        if mode < 2:
            continue
        score = (counts.count(mode) / len(counts), mode)
        if best is None or score > best[0]:
            best = (score, delim)
    return CsvFormat(encoding, best[1] if best else prefer)


def iter_row_offsets(path: str, fmt: CsvFormat, start: int = 0) -> Iterator[int]:
    """start 부터 비어 있지 않은 각 행의 시작 바이트 오프셋을 순서대로 낸다.

    바이너리로 읽는다 — 텍스트 모드의 tell() 은 바이트 위치가 아니다. 구분자·따옴표·
    CR·LF 는 모두 ASCII 이고 UTF-8 과 CP949 에서 멀티바이트 문자의 일부로 나타나지
    않으므로 디코딩 없이 바이트로 판정해도 경계가 맞는다.

    따옴표가 없는 줄은 LF 만 찾아 건너뛰고(빠른 경로), 따옴표가 있는 줄만 상태 기계로
    한 바이트씩 본다. 따옴표 안의 줄바꿈은 행 경계가 아니다. 빈 줄(LF 또는 CRLF 만
    있는 줄)은 csv.reader 가 [] 를 내는 줄이라 행으로 세지 않는다. 단독 CR 종결자는
    지원하지 않는다.
    """
    Q, D = ord(fmt.quotechar), ord(fmt.delimiter)
    qb = fmt.quotechar.encode("ascii")
    with open(path, "rb") as fh:
        fh.seek(start)
        base, buf, pos, eof = start, b"", 0, False
        row_start, content, state = start, False, _START

        while True:
            if state == _START and not content:
                # 행의 맨 앞이다 — 이 줄에 따옴표가 없으면 LF 까지 통째로 건너뛴다
                nl = buf.find(b"\n", pos)
                if nl == -1 and not eof:
                    chunk = fh.read(_CHUNK)
                    eof = not chunk
                    base, buf, pos = base + pos, buf[pos:] + chunk, 0
                    continue
                end = nl if nl != -1 else len(buf)
                if buf.find(qb, pos, end) == -1:
                    length = end - pos
                    if length and not (length == 1 and buf[pos] == 13):
                        yield row_start
                    if nl == -1:
                        return
                    pos = nl + 1
                    row_start = base + pos
                    continue

            # 느린 경로 — 행이 끝나거나 버퍼가 바닥날 때까지 한 바이트씩
            n, i, ended = len(buf), pos, False
            while i < n:
                if state == _QUOTED:
                    j = buf.find(qb, i)
                    if j == -1:
                        i = n
                        break
                    state, i = _QUOTE_IN_QUOTED, j + 1
                    continue
                c = buf[i]
                i += 1
                if c == 10:
                    if content:
                        yield row_start
                    pos, row_start, content, state = i, base + i, False, _START
                    ended = True
                    break
                if c == 13:
                    continue
                content = True
                if state == _START:
                    state = _QUOTED if c == Q else (_START if c == D else _FIELD)
                elif state == _FIELD:
                    if c == D:
                        state = _START
                else:                                  # _QUOTE_IN_QUOTED
                    state = _QUOTED if c == Q else (_START if c == D else _FIELD)
            if ended:
                continue
            if eof:
                if content:
                    yield row_start
                return
            chunk = fh.read(_CHUNK)
            eof = not chunk
            base, buf, pos = base + n, chunk, 0


def read_rows(path: str, fmt: CsvFormat, offset: int, n: int) -> list[list[str]]:
    """offset 으로 건너뛰어 비어 있지 않은 행을 최대 n 개 파싱한다.

    잘못된 바이트는 U+FFFD 로 바꿔 읽는다 — 한 바이트 때문에 페이지가 안 보이는 것보다
    보이고 경고하는 편이 낫다.
    """
    encoding = fmt.encoding
    if offset > 0 and _is_utf8(encoding):
        encoding = "utf-8"                        # 파일 중간에서 BOM 처리가 끼어들지 않게
    raw = open(path, "rb")
    raw.seek(offset)
    rows: list[list[str]] = []
    with io.TextIOWrapper(raw, encoding=encoding, errors="replace", newline="") as text:
        for row in csv.reader(text, delimiter=fmt.delimiter, quotechar=fmt.quotechar):
            if not row:
                continue
            rows.append(row)
            if len(rows) >= n:
                break
    return rows


def normalize_header(names: list[str]) -> list[str]:
    """빈 이름은 col_<위치>, 중복은 name.1, name.2 … 로 바꾼다. 표가 컬럼 이름을 키로 쓴다."""
    out: list[str] = []
    seen: set[str] = set()
    for i, name in enumerate(names, 1):
        base = name.strip() or f"col_{i}"
        candidate, k = base, 0
        while candidate in seen:
            k += 1
            candidate = f"{base}.{k}"
        seen.add(candidate)
        out.append(candidate)
    return out


def read_header(path: str, fmt: CsvFormat) -> tuple[list[str], int]:
    """(컬럼 이름, 첫 데이터 행의 바이트 오프셋). 데이터가 없으면 오프셋은 파일 크기다."""
    size = os.path.getsize(path)
    offsets = iter_row_offsets(path, fmt, _bom_len(path, fmt))
    try:
        header_at = next(offsets, None)
        if header_at is None:
            return [], size
        data_start = next(offsets, size)
    finally:
        offsets.close()
    return normalize_header(read_rows(path, fmt, header_at, 1)[0]), data_start
