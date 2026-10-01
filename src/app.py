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


def show_page(rows: list[list[str]], columns: list[str], first_row: int,
              fmt: CsvFormat, raw: bool) -> None:
    frame = present.to_frame(rows, columns, first_row, fmt.delimiter)
    coerced, types = present.coerce(frame, present.infer_types(frame))

    warn = present.page_warnings(frame)
    if warn["ragged_rows"]:
        st.warning(f"열 수가 헤더와 다른 행 {warn['ragged_rows']}개 — "
                   f"`{present.FLAG}` 열에 표시, 넘친 값은 `{present.EXTRA}` 열")
    if warn["decode_errors"]:
        st.warning(f"디코딩 오류 {warn['decode_errors']}건 (� 로 표시) — 사이드바에서 인코딩을 바꿔 보세요")

    tab_table, tab_summary = st.tabs(["표", "컬럼 요약"])
    with tab_table:
        if raw:
            st.dataframe(frame, height=TABLE_HEIGHT, width="stretch", key="table_raw")
        else:
            styled = present.style(coerced, types, present.null_mask(frame))
            st.dataframe(styled, height=TABLE_HEIGHT, width="stretch", key="table")
        st.caption("결측 셀은 주황색 · 정렬은 열 머리글 클릭 (현재 페이지 안에서)")
    with tab_summary:
        st.caption("모든 값은 **현재 페이지** 기준입니다.")
        st.dataframe(present.summarize(frame, coerced, types), hide_index=True,
                     width="stretch", key="summary")
        column = st.selectbox("차트로 볼 컬럼", present.data_columns(frame), key="chart_column")
        if column:
            kind, data = present.chart_data(frame, coerced, types, column)
            if data.empty:
                st.info("이 컬럼은 현재 페이지에 값이 없습니다.")
            elif kind == "line":
                st.line_chart(data)
            else:
                st.bar_chart(data)


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
    show_page(rows, columns, first_row, fmt, raw)


main()
