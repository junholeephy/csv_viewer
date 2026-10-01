"""뷰어 — 예제 테스트. 성질 검사는 test_viewer_pbt.py."""

import pandas as pd
import pytest

from core import load
from core.load import CsvFormat
from core.viewer import files, jobs, present

UTF8 = CsvFormat("utf-8-sig", ",")


# ── files ────────────────────────────────────────────────────────────────────

def test_lists_data_files_recursively_and_skips_hidden(tmp_path):
    (tmp_path / "a.csv").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.tsv").write_text("x")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "c.csv").write_text("x")
    (tmp_path / "d.json").write_text("x")
    assert files.list_data_files(tmp_path) == ["a.csv", "sub/b.tsv"]


def test_resolve_within_rejects_escape(tmp_path):
    with pytest.raises(ValueError):
        files.resolve_within(tmp_path, "../outside.csv")
    assert files.resolve_within(tmp_path, "x.csv") == (tmp_path / "x.csv").resolve()


# ── jobs ─────────────────────────────────────────────────────────────────────

def _big(tmp_path, n=1234):
    path = tmp_path / "big.csv"
    path.write_text("id,v\n" + "".join(f"{i},{i * 2}\n" for i in range(n)))
    return str(path)


def test_index_job_finds_every_page_start(tmp_path):
    path = _big(tmp_path)
    _, data_start = load.read_header(path, UTF8)
    job = jobs.IndexJob(path, UTF8, data_start)
    job.start()
    job.join(10)
    progress = job.progress()
    assert progress.done and progress.error is None and progress.rows_seen == 1234
    assert load.read_rows(path, UTF8, job.offset_of_row(1200), 100)[0] == ["1200", "2400"]
    assert job.last_reachable_page(100) == 12          # 0..12 → 13 페이지
    assert job.offset_of_row(1250) is None             # 마지막 행 너머


def test_offset_of_row_requires_stride_multiple(tmp_path):
    job = jobs.IndexJob(_big(tmp_path, 10), UTF8, 5)
    with pytest.raises(ValueError):
        job.offset_of_row(7)


def test_first_page_is_reachable_before_indexing(tmp_path):
    job = jobs.IndexJob(_big(tmp_path, 10), UTF8, 5)
    assert job.last_reachable_page(100) == 0


def test_index_errors_are_kept_not_raised(tmp_path):
    path = _big(tmp_path, 10)
    job = jobs.IndexJob(path, UTF8, 5)
    (tmp_path / "big.csv").unlink()
    job.start()
    job.join(10)
    assert job.progress().done and "FileNotFoundError" in job.progress().error


# ── present ──────────────────────────────────────────────────────────────────

def test_to_frame_pads_short_rows_and_collects_extras():
    frame = present.to_frame([["1", "2"], ["3"], ["4", "5", "6", "7"]], ["a", "b"], 100)
    assert list(frame.index) == [101, 102, 103]
    assert list(frame.columns) == [present.FLAG, "a", "b", present.EXTRA]
    assert frame.loc[102, "b"] is None
    assert frame.loc[103, present.EXTRA] == "6,7"
    assert frame.loc[103, present.FLAG] == "열 4/2"
    assert present.page_warnings(frame)["ragged_rows"] == 2


def test_clean_frame_has_no_flag_or_extra_columns():
    frame = present.to_frame([["1", "2"]], ["a", "b"], 0)
    assert list(frame.columns) == ["a", "b"]


@pytest.mark.parametrize("values, expected", [
    (["1", " -2 ", "NA", ""], "int"),
    (["1", "2.5", "1e3"], "float"),
    (["true", "FALSE"], "bool"),
    (["2024-01-02", "2024-01-03T10:00:00"], "datetime"),
    (["1", "x"], "str"),
    (["", "NA", None], "empty"),
])
def test_type_inference(values, expected):
    frame = present.to_frame([[v] for v in values], ["c"], 0)
    assert present.infer_types(frame) == {"c": expected}


def test_coerce_keeps_values_and_formats_numbers():
    frame = present.to_frame([["1234567", "2.50000"], ["NA", "0.1"]], ["i", "f"], 0)
    coerced, types = present.coerce(frame, present.infer_types(frame))
    assert types == {"i": "int", "f": "float"}
    assert str(coerced["i"].dtype) == "Int64" and coerced["i"].isna().tolist() == [False, True]
    html = present.style(coerced, types, present.null_mask(frame)).to_html()
    assert "1,234,567" in html and ">2.5<" in html


def test_coerce_falls_back_to_str_on_int64_overflow():
    frame = present.to_frame([["99999999999999999999"]], ["big"], 0)
    _, types = present.coerce(frame, present.infer_types(frame))
    assert types == {"big": "str"}


def test_summary_flags_almost_numeric_columns():
    frame = present.to_frame([[str(i)] for i in range(9)] + [["n/a?"]], ["c"], 0)
    coerced, types = present.coerce(frame, present.infer_types(frame))
    summary = present.summarize(frame, coerced, types)
    assert summary.loc[0, "타입"] == "str"
    assert summary.loc[0, "메모"] == "숫자처럼 보이지만 1개 실패"


def test_summary_numeric_stats():
    frame = present.to_frame([["1"], ["3"], [""]], ["c"], 0)
    coerced, types = present.coerce(frame, present.infer_types(frame))
    row = present.summarize(frame, coerced, types).iloc[0]
    assert (row["최소"], row["최대"], row["평균"], row["결측 %"]) == ("1", "3", "2", "33.3%")


@pytest.mark.parametrize("values, kind", [
    (["1", "2", "2", "3"], "bar"),
    (["a", "b", "a"], "bar"),
    (["2024-01-01", "2024-01-02"], "line"),
])
def test_chart_data_shapes(values, kind):
    frame = present.to_frame([[v] for v in values], ["c"], 0)
    coerced, types = present.coerce(frame, present.infer_types(frame))
    got_kind, data = present.chart_data(frame, coerced, types, "c")
    assert got_kind == kind and data["개수"].sum() == len(values)


def test_decode_errors_are_counted():
    frame = present.to_frame([["ok��"]], ["c"], 0)
    assert present.page_warnings(frame)["decode_errors"] == 2


def test_row_zero_is_data_start_even_without_data_rows(tmp_path):
    """PBT(test_pages_partition_the_file)가 찾은 회귀: 헤더만 있는 파일에서 None 이 나왔다."""
    path = tmp_path / "h.csv"
    path.write_text("a,b\n")
    job = jobs.IndexJob(str(path), UTF8, 4)
    job.start()
    job.join(10)
    assert job.offset_of_row(0) == 4 and job.last_reachable_page(100) == 0
