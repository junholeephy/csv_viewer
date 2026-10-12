"""CSV 뷰어 화면.

    streamlit run src/app.py                      # ./csv_files 의 파일을 본다
    streamlit run src/app.py -- --root <디렉터리>  # 다른 폴더를 볼 때

상대 경로는 실행한 위치(cwd) 기준이다. 접속 주소는 .streamlit/config.toml 에서
localhost 로 묶는다 — 그 파일도 cwd 기준으로 읽힌다.

여기는 위젯 배치와 세션 상태만 다룬다. 파일을 읽는 것은 core.load, 인덱싱은
core.viewer.jobs, 표·요약은 core.viewer.present 다 — 그쪽은 Streamlit 없이 테스트된다.

첫 페이지는 헤더 바로 뒤에서 읽으므로 인덱스를 기다리지 않는다. 나머지 페이지의 시작
위치는 백그라운드 인덱싱이 채워 가고, 채워진 범위까지 이동할 수 있다.
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

from core import load  # noqa: E402
from core.load import CsvFormat  # noqa: E402
from core.viewer import files, jobs, present  # noqa: E402

AUTO = "자동 감지"
PAGE_SIZES = (50, 100, 500)
DELIMITER_LABELS = {",": "쉼표 ,", "\t": "탭 \\t", ";": "세미콜론 ;", "|": "파이프 |"}
TABLE_HEIGHT = 640
DEFAULT_ROOT = "csv_files"


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="app.py", description="CSV 뷰어")
    ap.add_argument("--root", default=DEFAULT_ROOT,
                    help=f"파일을 고를 디렉터리 (기본: ./{DEFAULT_ROOT})")
    return ap.parse_known_args(argv)[0]


@st.cache_resource(max_entries=4, show_spinner=False, validate=lambda job: not job.abandoned)
def get_job(path: str, mtime_ns: int, size: int, encoding: str, delimiter: str,
            data_start: int) -> jobs.IndexJob:
    """(경로, 수정 시각, 크기, 포맷, 데이터 시작) 이 같으면 재실행 사이에 같은 작업을 쓴다."""
    job = jobs.IndexJob(path, CsvFormat(encoding, delimiter), data_start)
    job.start()
    return job


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:,.1f} {unit}"
        n /= 1024
    return f"{n} B"


# ── 세션 상태 ────────────────────────────────────────────────────────────────

def _reset_page() -> None:
    st.session_state.page_no = 1


def _change_page_size() -> None:
    """같은 첫 행이 보이는 페이지로 옮긴다."""
    ss = st.session_state
    old, new = ss.get("page_size_cur", 100), ss.page_size
    first_row = (ss.get("page_no", 1) - 1) * old
    ss.page_no = first_row // new + 1
    ss.page_size_cur = new


def _go(target: int, last_page: int, done: bool) -> None:
    """target 은 1부터 센다. 아직 인덱싱되지 않은 페이지면 머무르고 알린다."""
    ss = st.session_state
    if target > last_page:
        if not done:
            ss.flash = "아직 인덱싱되지 않은 페이지입니다. 진행 상황을 보고 다시 시도하세요."
        target = last_page
    ss.page_no = max(1, target)


# ── 화면 조각 ────────────────────────────────────────────────────────────────

def sidebar(root: Path) -> tuple[str | None, str, str, int, bool]:
    with st.sidebar:
        st.header("CSV Viewer")
        st.caption(f"root: `{root}`")
        choices = files.list_data_files(root)
        if not choices:
            st.info(f"`{root}` 에 .csv / .tsv / .txt 파일이 없습니다. 파일을 넣고 새로고침하세요.")
            st.stop()
        rel = st.selectbox("파일", choices, index=None, placeholder="파일을 고르세요",
                           key="file", on_change=_reset_page)
        encoding = st.selectbox("인코딩", (AUTO, *load.ENCODINGS), key="encoding",
                                on_change=_reset_page)
        delimiter = st.selectbox("구분자", (AUTO, *DELIMITER_LABELS), key="delimiter",
                                 format_func=lambda d: DELIMITER_LABELS.get(d, d),
                                 on_change=_reset_page)
        page_size = st.radio("페이지 크기", PAGE_SIZES, index=PAGE_SIZES.index(100),
                             horizontal=True, key="page_size", on_change=_change_page_size)
        raw = st.toggle("원본 보기", key="raw", help="변환·포맷 없이 파일의 문자열 그대로")
    return rel, encoding, delimiter, page_size, raw


def _move_column(key: str, pick_key: str, front: bool) -> None:
    ss = st.session_state
    column = ss.get(pick_key)
    if column is None:
        return
    order = [c for c in ss[key] if c != column]
    ss[key] = [column, *order] if front else [*order, column]


def _reset_columns(key: str, pin_key: str, columns: list[str]) -> None:
    st.session_state[key] = list(columns)
    st.session_state[pin_key] = 0


def column_controls(rel: str, columns: list[str]) -> tuple[list[str], int]:
    """표시할 컬럼·순서와 왼쪽 고정 개수. 파일마다 따로 기억한다.

    표 머리글을 드래그해도 순서는 바뀌지만 페이지를 넘기면 표를 새로 그려 원래대로
    돌아간다. 그래서 순서를 세션 상태로 들고 있는다.
    """
    ss = st.session_state
    key, pin_key, pick_key = f"order::{rel}", f"pin::{rel}", f"pick::{rel}"
    # 인코딩·구분자를 바꾸면 헤더가 달라질 수 있다 — 없어진 이름은 버린다
    ss[key] = [c for c in ss[key] if c in columns] if key in ss else list(columns)
    ss.setdefault(pin_key, 0)

    with st.sidebar:
        st.divider()
        st.markdown("**컬럼 순서·표시**")
        order = st.multiselect(
            "컬럼 순서", columns, key=key, label_visibility="collapsed",
            help="고른 순서대로 표에 나옵니다. 빼면 숨겨집니다. 다시 넣은 컬럼은 맨 뒤에 붙습니다.")
        pick = st.selectbox("옮길 컬럼", order, index=None, placeholder="옮길 컬럼",
                            key=pick_key, label_visibility="collapsed")
        c1, c2, c3 = st.columns(3)
        c1.button("맨 앞", key=f"front::{rel}", width="stretch", disabled=pick is None,
                  on_click=_move_column, args=(key, pick_key, True))
        c2.button("맨 뒤", key=f"back::{rel}", width="stretch", disabled=pick is None,
                  on_click=_move_column, args=(key, pick_key, False))
        c3.button("초기화", key=f"reset::{rel}", width="stretch",
                  on_click=_reset_columns, args=(key, pin_key, columns))
        pinned = st.number_input("왼쪽 고정 컬럼 수", min_value=0, max_value=3, step=1,
                                 key=pin_key, help="순서상 앞에서부터 이 개수만큼 가로 스크롤해도 보이게")
        if not order:
            st.warning("표시할 컬럼이 없어 전체를 보여줍니다.")
    return (order or list(columns)), int(pinned)


@st.fragment(run_every=0.5)
def progress_live(job: jobs.IndexJob) -> None:
    """인덱싱 중에만 그려진다. 끝나는 순간 전체를 한 번 다시 그려 내비게이션을 갱신한다."""
    p = job.progress()
    if p.done:
        st.rerun()
    share = p.bytes_done / p.total_bytes if p.total_bytes else 1.0
    st.progress(min(share, 1.0), text=f"인덱싱 중 … {p.rows_seen:,}행 확인 ({share:.0%})")


def progress_panel(job: jobs.IndexJob, page_size: int) -> None:
    p = job.progress()
    if not p.done:
        progress_live(job)
    elif p.error:
        st.error(f"인덱싱 중단: {p.error} — {p.rows_seen:,}행까지는 이동할 수 있습니다.")
    else:
        pages = max(1, -(-p.rows_seen // page_size))
        st.caption(f"전체 {p.rows_seen:,}행 · {pages:,}페이지")


def pager(job: jobs.IndexJob, page_size: int) -> int:
    """현재 페이지(1부터)를 돌려준다."""
    ss = st.session_state
    done = job.progress().done
    last = job.last_reachable_page(page_size) + 1
    ss.page_no = min(max(1, ss.get("page_no", 1)), last)

    cols = st.columns([1, 1, 2, 1, 1, 4], vertical_alignment="bottom")
    cols[0].button("⏮", key="nav_first", help="처음", width="stretch",
                   on_click=_go, args=(1, last, done), disabled=ss.page_no == 1)
    cols[1].button("◀", key="nav_prev", help="이전", width="stretch",
                   on_click=_go, args=(ss.page_no - 1, last, done), disabled=ss.page_no == 1)
    cols[2].number_input("페이지", min_value=1, max_value=last, step=1, key="page_no",
                         label_visibility="collapsed")
    cols[3].button("▶", key="nav_next", help="다음", width="stretch",
                   on_click=_go, args=(ss.page_no + 1, last, done),
                   disabled=done and ss.page_no >= last)
    cols[4].button("⏭", key="nav_last", help="끝 (인덱싱이 끝나야 열립니다)", width="stretch",
                   on_click=_go, args=(last, last, done), disabled=not done)
    first = (ss.page_no - 1) * page_size + 1
    cols[5].caption(f"{ss.page_no:,} / {last:,}{'' if done else '+'} 페이지 · "
                    f"{first:,}행부터 {page_size}행")
    if msg := ss.pop("flash", None):
        st.toast(msg)
    return ss.page_no


def detail_panel(frame, position: int, order: list[str]) -> None:
    """선택한 행의 값 전체. 표 셀은 잘려 있으므로 여기서는 원본 문자열을 그대로 보인다."""
    short, long = present.row_detail(frame, position, order)
    with st.container(border=True):
        st.markdown(f"**{frame.index[position]:,}행 상세**")
        if not short.empty:
            st.dataframe(short, hide_index=True, width="stretch", key="detail_short")
        for column, value in long:
            st.caption(f"`{column}` · {len(value):,}자")
            tall = len(value) > 1500 or value.count("\n") > 12
            st.code(value, language=None, wrap_lines=True, height=320 if tall else "content")
        row = frame.iloc[position]
        for column in order:                      # 길이와 상관없이 JSON 이면 트리로도
            parsed = present.parse_json(row[column])
            if parsed is not None:
                with st.expander(f"`{column}` — JSON 트리"):
                    st.json(parsed, expanded=1)


def show_page(rows: list[list[str]], columns: list[str], first_row: int, fmt: CsvFormat,
              raw: bool, order: list[str], pinned: int, table_key: str) -> None:
    frame = present.to_frame(rows, columns, first_row, fmt.delimiter)
    coerced, types = present.coerce(frame, present.infer_types(frame))

    warn = present.page_warnings(frame)
    if warn["ragged_rows"]:
        st.warning(f"열 수가 헤더와 다른 행 {warn['ragged_rows']}개 — "
                   f"`{present.FLAG}` 열에 표시, 넘친 값은 `{present.EXTRA}` 열")
    if warn["decode_errors"]:
        st.warning(f"디코딩 오류 {warn['decode_errors']}건 (� 로 표시) — 사이드바에서 인코딩을 바꿔 보세요")

    shown = ([present.FLAG] if present.FLAG in frame else []) + order + \
            ([present.EXTRA] if present.EXTRA in frame else [])
    config = {c: st.column_config.Column(pinned=True) for c in order[:pinned]}

    tab_table, tab_summary = st.tabs(["표", "컬럼 요약"])
    with tab_table:
        if raw:
            data = present.truncate(frame)
        else:
            data = present.style(present.truncate(coerced), types, present.null_mask(frame))
        # column_order 를 주면 Streamlit 이 인덱스(원본 행 번호)를 숨긴다 — 명시해서 살린다
        event = st.dataframe(data, height=TABLE_HEIGHT, width="stretch", column_order=shown,
                             hide_index=False,
                             column_config=config, on_select="rerun",
                             selection_mode="single-row", key=table_key)
        st.caption(f"결측 셀은 주황색 · 정렬은 열 머리글 클릭 (현재 페이지 안에서) · "
                   f"셀은 앞 {present.CELL_LIMIT}자까지 — **행을 클릭하면 전체 내용**")
        selected = event.selection.rows if event is not None else []
        if selected:
            detail_panel(frame, selected[0], order)
    with tab_summary:
        st.caption("모든 값은 **현재 페이지** 기준입니다.")
        summary = present.summarize(frame, coerced, types)
        summary = summary.set_index("컬럼").loc[order].reset_index()
        st.dataframe(summary, hide_index=True, width="stretch", key="summary")
        column = st.selectbox("차트로 볼 컬럼", order, key="chart_column")
        if column:
            kind, chart = present.chart_data(frame, coerced, types, column)
            if chart.empty:
                st.info("이 컬럼은 현재 페이지에 값이 없습니다.")
            elif kind == "line":
                st.line_chart(chart)
            else:
                st.bar_chart(chart)


# ── 진입 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="CSV Viewer", page_icon="📄", layout="wide")
    args = parse_args(sys.argv[1:])
    root = Path(args.root).expanduser().resolve()
    if args.root == DEFAULT_ROOT and not root.exists():
        root.mkdir()                              # 처음 실행 — 넣을 자리를 만들어 둔다
    if not root.is_dir():
        st.error(f"--root 가 디렉터리가 아닙니다: {root}")
        st.stop()

    rel, enc_choice, delim_choice, page_size, raw = sidebar(root)
    st.session_state.setdefault("page_size_cur", page_size)
    if rel is None:
        st.title("CSV Viewer")
        st.info("왼쪽에서 파일을 고르세요. 큰 파일도 첫 페이지는 바로 열립니다.")
        return

    try:
        path = files.resolve_within(root, rel)
        stat = path.stat()
        if stat.st_size == 0:
            st.subheader(rel)
            st.info("빈 파일입니다.")
            return
        sniffed = load.sniff_format(str(path), None if enc_choice == AUTO else enc_choice)
        fmt = CsvFormat(sniffed.encoding,
                        sniffed.delimiter if delim_choice == AUTO else delim_choice)
        columns, data_start = load.read_header(str(path), fmt)
    except (OSError, ValueError, LookupError) as exc:
        st.error(f"파일을 열 수 없습니다: {type(exc).__name__}: {exc}")
        return

    st.subheader(rel)
    st.caption(f"{human_size(stat.st_size)} · 인코딩 `{fmt.encoding}` · "
               f"구분자 {DELIMITER_LABELS[fmt.delimiter]} · 컬럼 {len(columns)}개")
    if not columns:
        st.info("내용이 있는 행이 없습니다.")
        return

    job = get_job(str(path), stat.st_mtime_ns, stat.st_size, fmt.encoding, fmt.delimiter,
                  data_start)
    previous = st.session_state.get("job")
    if previous is not None and previous is not job:
        previous.stop()                          # 다른 파일·포맷으로 바뀌었다
    st.session_state.job = job

    progress_panel(job, page_size)
    if data_start >= stat.st_size:
        st.info(f"헤더만 있고 데이터 행이 없습니다. 컬럼: {', '.join(columns)}")
        return

    order, pinned = column_controls(rel, columns)
    page_no = pager(job, page_size)
    first_row = (page_no - 1) * page_size
    offset = job.offset_of_row(first_row)
    if offset is None:                            # 파일이 바뀐 직후 등 — 첫 페이지로
        first_row, offset = 0, data_start
    try:
        rows = load.read_rows(str(path), fmt, offset, page_size)
    except (OSError, ValueError, csv.Error) as exc:  # 앱은 살려 두고 다른 페이지로 갈 수 있게
        st.error(f"페이지를 읽을 수 없습니다: {type(exc).__name__}")
        return
    # 페이지·크기·파일·보기가 바뀌면 키가 달라져 행 선택이 풀린다
    table_key = f"table::{rel}::{fmt.encoding}::{fmt.delimiter}::{page_size}::{first_row}::{raw}"
    show_page(rows, columns, first_row, fmt, raw, order, pinned, table_key)


main()
