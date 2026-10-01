"""페이지 읽기 — 예제 테스트. 성질 검사는 test_load_paged_pbt.py."""

import pytest

from core import load
from core.load import CsvFormat

UTF8 = CsvFormat("utf-8-sig", ",")


def _write(tmp_path, data, name="t.csv"):
    path = tmp_path / name
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return str(path)


def _all_rows(path, fmt):
    start = load._bom_len(path, fmt)
    return [load.read_rows(path, fmt, off, 1)[0] for off in load.iter_row_offsets(path, fmt, start)]


@pytest.mark.parametrize("delim", [",", "\t", ";", "|"])
def test_sniff_finds_delimiter(tmp_path, delim):
    text = "\n".join(delim.join(f"{c}{i}" for c in "abc") for i in range(10)) + "\n"
    assert load.sniff_format(_write(tmp_path, text)).delimiter == delim


def test_sniff_prefers_tab_for_tsv_when_ambiguous(tmp_path):
    path = _write(tmp_path, "single\nvalue\n", "t.tsv")
    assert load.sniff_format(path).delimiter == "\t"


def test_sniff_detects_cp949(tmp_path):
    path = _write(tmp_path, "이름,값\n가나,1\n".encode("cp949"))
    assert load.sniff_format(path).encoding == "cp949"


def test_sniff_keeps_explicit_encoding(tmp_path):
    path = _write(tmp_path, "a,b\n1,2\n")
    assert load.sniff_format(path, encoding="latin-1").encoding == "latin-1"


def test_quoted_newlines_and_escaped_quotes_stay_in_one_row(tmp_path):
    path = _write(tmp_path, 'h1,h2\r\n"line1\nline2","say ""hi"""\r\nx,y\r\n')
    assert _all_rows(path, UTF8) == [["h1", "h2"], ["line1\nline2", 'say "hi"'], ["x", "y"]]


def test_quote_in_middle_of_field_is_literal(tmp_path):
    path = _write(tmp_path, 'h\nab"c\nd\n')
    assert _all_rows(path, UTF8) == [["h"], ['ab"c'], ["d"]]


def test_blank_lines_are_not_rows(tmp_path):
    path = _write(tmp_path, "h\n\n1\r\n\r\n2\n")
    assert _all_rows(path, UTF8) == [["h"], ["1"], ["2"]]


def test_last_row_without_newline_is_read(tmp_path):
    path = _write(tmp_path, "h\n1\n2")
    assert _all_rows(path, UTF8) == [["h"], ["1"], ["2"]]


def test_chunk_boundaries_do_not_change_offsets(tmp_path, monkeypatch):
    text = 'a,b\n' + "".join(f'"{i}\n{i}",x{i}\n' for i in range(200))
    path = _write(tmp_path, text)
    expected = list(load.iter_row_offsets(path, UTF8))
    monkeypatch.setattr(load, "_CHUNK", 5)
    assert list(load.iter_row_offsets(path, UTF8)) == expected


def test_header_strips_bom_and_points_at_first_data_row(tmp_path):
    path = _write(tmp_path, b"\xef\xbb\xbfa,b\n1,2\n")
    columns, data_start = load.read_header(path, UTF8)
    assert columns == ["a", "b"]
    assert load.read_rows(path, UTF8, data_start, 10) == [["1", "2"]]


def test_header_names_are_normalised():
    assert load.normalize_header([" x ", "", "x", "x", "col_2"]) == \
        ["x", "col_2", "x.1", "x.2", "col_2.1"]


def test_empty_file_has_no_header(tmp_path):
    path = _write(tmp_path, b"")
    assert load.read_header(path, UTF8) == ([], 0)


def test_header_only_file_has_data_start_at_eof(tmp_path):
    path = _write(tmp_path, "a,b\n")
    columns, data_start = load.read_header(path, UTF8)
    assert columns == ["a", "b"] and data_start == 4
    assert load.read_rows(path, UTF8, data_start, 10) == []


def test_bad_bytes_are_replaced_not_raised(tmp_path):
    path = _write(tmp_path, b"h\nok\xff\n")
    assert load.read_rows(path, UTF8, 2, 5) == [["ok�"]]


def test_read_rows_caps_at_n(tmp_path):
    path = _write(tmp_path, "h\n" + "".join(f"{i}\n" for i in range(10)))
    assert load.read_rows(path, UTF8, 2, 3) == [["0"], ["1"], ["2"]]
