"""페이지 읽기 — 성질 검사 (Hypothesis).

TP-1 오라클: 오프셋마다 1행 읽은 결과 == csv.reader 로 처음부터 순차 파싱한 결과
TP-2 왕복:   csv.writer 로 쓴 (헤더, 행) == read_header + read_rows 로 읽은 것
TP-3 불변식: 오프셋은 강하게 증가하고 파일 안에 있으며, 개수 == 비어 있지 않은 행 수
"""

import os
import tempfile
from contextlib import contextmanager

from hypothesis import given
from hypothesis import strategies as st

from core import load
from strategies import csv_cases

chunks = st.sampled_from([3, 17, 1 << 20])        # 청크 경계가 아무 데나 걸리게


@contextmanager
def written(data: bytes, chunk: int):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, data)
    os.close(fd)
    original, load._CHUNK = load._CHUNK, chunk
    try:
        yield path
    finally:
        load._CHUNK = original
        os.remove(path)


@given(csv_cases(), chunks)
def test_offsets_agree_with_sequential_parse(case, chunk):
    with written(case.data, chunk) as path:
        start = load._bom_len(path, case.fmt)
        got = [load.read_rows(path, case.fmt, off, 1)[0]
               for off in load.iter_row_offsets(path, case.fmt, start)]
    assert got == case.rows


@given(csv_cases(ragged=False, with_header=True), chunks)
def test_header_and_rows_round_trip(case, chunk):
    with written(case.data, chunk) as path:
        columns, data_start = load.read_header(path, case.fmt)
        rows = load.read_rows(path, case.fmt, data_start, len(case.rows) + 5)
    assert columns == case.rows[0]
    assert rows == case.rows[1:]


@given(csv_cases(), chunks)
def test_offsets_are_increasing_and_inside_the_file(case, chunk):
    with written(case.data, chunk) as path:
        offsets = list(load.iter_row_offsets(path, case.fmt, load._bom_len(path, case.fmt)))
    assert all(a < b for a, b in zip(offsets, offsets[1:]))
    assert all(0 <= off < len(case.data) for off in offsets)
    assert len(offsets) == len(case.rows)
