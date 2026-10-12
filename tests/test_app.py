"""화면 스모크 — Streamlit AppTest 로 실제 스크립트를 돌린다 (브라우저 없음)."""

import json
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
    (tmp_path / "long.csv").write_text(
        'id,body,js\n1,"' + "x" * 600 + '\nline2","{""a"": [1, 2]}"\n2,short,NA\n')
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


def test_without_root_it_uses_csv_files_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["app.py"])
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert (tmp_path / "csv_files").is_dir()            # 처음 실행이면 만들어 둔다
    assert "파일이 없습니다" in at.info[0].value

    (tmp_path / "csv_files" / "a.csv").write_text("x,y\n1,2\n")
    at.run()
    _open(at, "a.csv")
    assert len(at.dataframe[0].value) == 1


def _table_key(name, first_row=0, size=100):
    return f"table::{name}::utf-8-sig::,::{size}::{first_row}::False"


def test_row_click_opens_detail_with_full_text(app):
    _open(app, "long.csv")
    assert len(app.dataframe[0].value.loc[1, "body"]) == 301          # 표 셀은 잘려 있다
    assert not any("상세" in m.value for m in app.markdown)

    app.session_state[_table_key("long.csv")] = {"selection": {"rows": [0], "columns": [], "cells": []}}
    app.run()
    assert not app.exception
    assert any(m.value == "**1행 상세**" for m in app.markdown)
    assert [len(c.value) for c in app.code] == [606]                  # 전체 본문
    assert len(app.json) == 1                                          # 짧은 JSON 도 트리로


def test_column_order_pin_and_hide_survive_paging(app):
    _open(app, "big.csv")
    app.session_state["job"].join(10)
    app.run()
    app.multiselect(key="order::big.csv").set_value(["score", "id"]).run()  # name·day 숨김
    app.number_input(key="pin::big.csv").set_value(1).run()
    table = app.dataframe[0].proto
    assert list(table.column_order) == ["score", "id"]
    config = json.loads(table.columns)
    assert config["score"] == {"pinned": True}
    assert not config.get("_index", {}).get("hidden"), "원본 행 번호가 사라졌다"

    app.button(key="nav_next").click().run()
    assert list(app.dataframe[0].proto.column_order) == ["score", "id"]
    assert app.selectbox(key="chart_column").options == ["score", "id"]

    app.selectbox(key="pick::big.csv").select("id").run()
    app.button(key="front::big.csv").click().run()
    assert list(app.dataframe[0].proto.column_order) == ["id", "score"]

    app.button(key="reset::big.csv").click().run()
    assert list(app.dataframe[0].proto.column_order) == ["id", "name", "score", "day"]
