"""뷰어 — 성질 검사 (Hypothesis).

TP-4 불변식: 체크포인트로 읽은 페이지를 이어 붙이면 전체 행, 마지막 외에는 꽉 찬 페이지
TP-5 오라클: IndexJob 의 체크포인트 == iter_row_offsets 를 stride 간격으로 뽑은 것
TP-6 불변식: to_frame 은 행 수·헤더 순서·행 번호를 보존한다
TP-7 불변식: 타입 변환은 비결측 셀을 결측으로 만들지 않는다 (조용한 값 손실 없음)
TP-8 불변식: resolve_within 은 루트 밖 경로를 돌려주지 않는다
"""

import os
import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from core import load
from core.schema import is_null
from core.viewer import files, jobs, present
from strategies import csv_cases, fields


def _job_for(case, stride):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, case.data)
    os.close(fd)
    columns, data_start = load.read_header(path, case.fmt)
    job = jobs.IndexJob(path, case.fmt, data_start, stride=stride)
    job.start()
    job.join(30)
    return path, data_start, job


@given(csv_cases(ragged=False, with_header=True, max_rows=80),
       st.sampled_from([1, 2, 5]), st.integers(1, 4))
def test_pages_partition_the_file(case, stride, multiple):
    page_size = stride * multiple                     # 실제 50/100/500 과 같은 관계: stride | page_size
    path, _, job = _job_for(case, stride)
    try:
        last = job.last_reachable_page(page_size)
        pages = [load.read_rows(path, case.fmt, job.offset_of_row(p * page_size), page_size)
                 for p in range(last + 1)]
    finally:
        os.remove(path)
    data = case.rows[1:]
    assert [r for page in pages for r in page] == data
    assert all(len(page) == page_size for page in pages[:-1])
    assert len(pages) == max(1, -(-len(data) // page_size))


@given(csv_cases(with_header=True, max_rows=80), st.sampled_from([1, 3, 50]))
def test_checkpoints_match_scanner(case, stride):
    path, data_start, job = _job_for(case, stride)
    try:
        expected = list(load.iter_row_offsets(path, case.fmt, data_start))
        progress = job.progress()
        got = [job.offset_of_row(r) for r in range(0, len(expected), stride)]
    finally:
        os.remove(path)
    assert progress.done and progress.rows_seen == len(expected)
    assert got == expected[::stride]


rows_st = st.lists(st.lists(fields, min_size=0, max_size=7), max_size=30)


@given(rows_st, st.integers(1, 5), st.integers(0, 10_000))
def test_to_frame_preserves_shape(rows, width, first_row):
    rows = [r for r in rows if r]                     # 빈 행은 리더가 이미 걸러낸다
    columns = [f"c{i}" for i in range(width)]
    frame = present.to_frame(rows, columns, first_row)
    assert len(frame) == len(rows)
    assert present.data_columns(frame) == columns
    assert list(frame.index) == list(range(first_row + 1, first_row + 1 + len(rows)))


cell = st.one_of(
    st.from_regex(r"[+-]?\d{1,25}", fullmatch=True),
    st.from_regex(r"[+-]?\d{1,5}\.\d{0,5}([eE][+-]?\d{1,3})?", fullmatch=True),
    st.sampled_from(["true", "FALSE", "2024-02-29", "2024-01-01T12:30:00", "2024-01-01T00:00:00+09:00",
                     "", "NA", "null", "-", "x", " 7 "]),
)


@given(st.lists(st.lists(cell, min_size=3, max_size=3), min_size=1, max_size=40))
def test_coerce_never_loses_values(rows):
    frame = present.to_frame(rows, ["a", "b", "c"], 0)
    coerced, types = present.coerce(frame, present.infer_types(frame))
    for column, kind in types.items():
        if kind in ("str", "empty"):
            continue
        original = frame[column].map(lambda v: not is_null(v)).to_numpy()
        assert not (original & coerced[column].isna().to_numpy()).any(), column


segments = st.sampled_from(["..", ".", "a", "b", "sub", "x.csv", "/etc", "/"])


@given(st.lists(segments, min_size=1, max_size=6))
def test_resolve_within_never_escapes(parts):
    root = Path(tempfile.gettempdir()) / "viewer-root"
    rel = "/".join(parts)
    try:
        resolved = files.resolve_within(root, rel)
    except ValueError:
        return
    assert resolved.is_relative_to(root.resolve())
