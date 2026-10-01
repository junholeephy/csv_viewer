"""Hypothesis 전략. 여러 테스트 파일이 같은 CSV 생성기를 쓴다."""

import csv
import io
from dataclasses import dataclass

from hypothesis import strategies as st

from core.load import DELIMITERS, CsvFormat

# 구분자·따옴표·줄바꿈·공백·한글(cp949 로도 인코딩되는 것만)을 섞는다
_PIECES = list("abXY09 ,;\t|\"\n\r") + ["\r\n", "가", "나", "한글", ""]
fields = st.lists(st.sampled_from(_PIECES), max_size=6).map("".join)
names = st.text(alphabet="abcdefgh_", min_size=1, max_size=6)


@dataclass(frozen=True)
class CsvCase:
    data: bytes
    fmt: CsvFormat
    rows: list[list[str]]          # 빈 줄을 뺀, csv.reader 가 내야 할 행들


def _line(row: list[str], delim: str, term: str) -> str:
    buf = io.StringIO()
    csv.writer(buf, delimiter=delim, lineterminator=term).writerow(row)
    return buf.getvalue()


@st.composite
def csv_cases(draw, *, ragged: bool = True, blank_lines: bool = True,
              with_header: bool = False, max_rows: int = 60) -> CsvCase:
    delim = draw(st.sampled_from(DELIMITERS))
    term = draw(st.sampled_from(["\n", "\r\n"]))
    encoding = draw(st.sampled_from(["utf-8-sig", "cp949"]))
    width = draw(st.integers(1, 6))
    row = (st.lists(fields, min_size=1, max_size=8) if ragged
           else st.lists(fields, min_size=width, max_size=width))

    rows = draw(st.lists(row, max_size=max_rows))
    if with_header:
        rows = [draw(st.lists(names, min_size=width, max_size=width, unique=True)), *rows]

    text = ""
    for r in rows:
        if blank_lines and draw(st.booleans()):
            text += term * draw(st.integers(1, 2))
        text += _line(r, delim, term)
    if rows and draw(st.booleans()):
        text = text[: -len(term)]                 # 마지막 줄바꿈 없는 파일
    return CsvCase(text.encode(encoding), CsvFormat(encoding, delim), rows)
