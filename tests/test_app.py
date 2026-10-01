"""화면 스모크 — Streamlit AppTest 로 실제 스크립트를 돌린다 (브라우저 없음)."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "src" / "app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    (tmp_path / "big.csv").write_text(
        "id,name,score,day\n"
        + "".join(f"{i},n{i},{'' if i % 7 == 0 else i / 4},2024-01-{i % 28 + 1:02d}\n"
                  for i in range(1, 251)))
    (tmp_path / "empty.csv").write_text("")
    (tmp_path / "header_only.csv").write_text("a,b\n")
    monkeypatch.setattr(sys, "argv", ["app.py", "--root", str(tmp_path)])
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def _open(at, name):
    at.selectbox(key="file").select(name).run()
    assert not at.exception, at.exception


def test_landing_page_asks_for_a_file(app):
    assert not app.exception
    assert "파일을 고르세요" in app.info[0].value


def test_first_page_renders_then_next_page_after_indexing(app):
    _open(app, "big.csv")
    first = app.dataframe[0].value
    assert list(first.index[:2]) == [1, 2] and len(first) == 100
    assert app.session_state["page_no"] == 1

    app.session_state["job"].join(10)
    app.run()
    assert "전체 250행 · 3페이지" in [c.value for c in app.caption]

    app.button(key="nav_next").click().run()
    assert app.session_state["page_no"] == 2
    assert app.dataframe[0].value.index[0] == 101

    app.button(key="nav_last").click().run()
    assert len(app.dataframe[0].value) == 50


def test_page_size_change_keeps_first_row_visible(app):
    _open(app, "big.csv")
    app.session_state["job"].join(10)
    app.run()
    app.button(key="nav_next").click().run()        # 101행부터
    app.radio(key="page_size").set_value(50).run()
    assert app.session_state["page_no"] == 3        # 101행 = 50행 페이지의 3번째
    assert app.dataframe[0].value.index[0] == 101


def test_empty_and_header_only_files_do_not_crash(app):
    _open(app, "empty.csv")
    assert "빈 파일" in app.info[0].value
    _open(app, "header_only.csv")
    assert any("데이터 행이 없습니다" in i.value for i in app.info)
