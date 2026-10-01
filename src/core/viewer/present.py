"""한 페이지분 행을 읽기 좋은 표와 요약으로 바꾼다.

모든 판단은 **현재 페이지**만 보고 한다 — 파일 전체를 읽지 않는 것이 이 뷰어의 전제다.
타입은 페이지의 비결측 값이 전부 해석될 때만 붙인다. 하나라도 어긋나면 문자열로 둬서,
표가 원본 값을 조용히 바꾸거나 숨기지 않게 한다.
"""

import re
from datetime import datetime

import numpy as np
import pandas as pd

from ..schema import is_null

FLAG = "⚠"
EXTRA = "…extra"
NULL_STYLE = "background-color: rgba(255, 170, 0, 0.28)"   # 라이트·다크 테마 모두에서 보이게

_INT = re.compile(r"[+-]?\d+")
_FLOAT = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")


def data_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c not in (FLAG, EXTRA)]


def to_frame(rows: list[list[str]], columns: list[str], first_row: int,
             delimiter: str = ",") -> pd.DataFrame:
    """인덱스는 1부터 세는 원본 데이터 행 번호다.

    열이 모자란 행은 결측으로 채우고, 넘치는 값은 EXTRA 컬럼에 구분자로 이어 붙인다.
    그런 행이 있으면 맨 앞 FLAG 컬럼에 "열 실제/기대" 를 적는다.
    """
    width = len(columns)
    data, extras, flags = [], [], []
    for row in rows:
        n = len(row)
        data.append(row[:width] + [None] * (width - n))
        extras.append(delimiter.join(row[width:]) if n > width else None)
        flags.append(None if n == width else f"열 {n}/{width}")
    frame = pd.DataFrame(data, columns=columns, dtype=object)
    if any(e is not None for e in extras):
        frame[EXTRA] = pd.Series(extras, dtype=object)
    if any(f is not None for f in flags):
        frame.insert(0, FLAG, pd.Series(flags, dtype=object))
    frame.index = pd.RangeIndex(first_row + 1, first_row + 1 + len(rows), name="#")
    return frame


def _non_null(series: pd.Series) -> list[str]:
    return [v.strip() for v in series if not is_null(v)]


def _is_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def _type_of(values: list[str]) -> str:
    if not values:
        return "empty"
    if all(_INT.fullmatch(v) for v in values):
        return "int"
    if all(_FLOAT.fullmatch(v) for v in values):
        return "float"
    if all(v.lower() in ("true", "false") for v in values):
        return "bool"
    if all(_is_datetime(v) for v in values):
        return "datetime"
    return "str"


def infer_types(frame: pd.DataFrame) -> dict[str, str]:
    """"int" | "float" | "bool" | "datetime" | "str" | "empty" — 이 순서로 처음 맞는 것."""
    return {c: _type_of(_non_null(frame[c])) for c in data_columns(frame)}


def _convert(series: pd.Series, kind: str) -> pd.Series:
    # Series.map 은 None 을 NaN 으로 바꾸므로 리스트로 다룬다
    clean = [None if is_null(v) else v.strip() for v in series]
    if kind == "int":
        values = [None if v is None else int(v) for v in clean]
        if any(v is not None and not -2**63 <= v < 2**63 for v in values):
            raise OverflowError("int64 범위 밖")
        return pd.array(values, dtype="Int64")
    if kind == "float":
        return pd.array([None if v is None else float(v) for v in clean], dtype="Float64")
    if kind == "bool":
        return pd.array([None if v is None else v.lower() == "true" for v in clean], dtype="boolean")
    if kind == "datetime":
        return pd.to_datetime(pd.Series(clean, index=series.index), format="ISO8601")
    raise ValueError(kind)


def coerce(frame: pd.DataFrame, types: dict[str, str]) -> tuple[pd.DataFrame, dict[str, str]]:
    """타입대로 변환한 사본과, 실제로 적용된 타입을 돌려준다.

    변환에 실패한 컬럼(int64 범위 밖, 시간대가 섞인 날짜 등)은 원본 문자열로 남기고
    타입을 "str" 로 내린다 — 반쯤 변환된 표보다 정직하다.
    """
    out = frame.copy()
    applied = dict(types)
    for column, kind in types.items():
        if kind in ("str", "empty"):
            continue
        try:
            out[column] = _convert(frame[column], kind)
        except (ValueError, OverflowError, TypeError):
            applied[column] = "str"
    return out, applied


def null_mask(frame: pd.DataFrame) -> pd.DataFrame:
    """결측 셀(schema.NULL_TOKENS 기준)이면 True. FLAG·EXTRA 컬럼은 항상 False."""
    mask = pd.DataFrame(False, index=frame.index, columns=frame.columns)
    for column in data_columns(frame):
        mask[column] = frame[column].map(is_null).astype(bool)
    return mask


def _fmt_float(value: float) -> str:
    text = f"{value:,.4f}".rstrip("0").rstrip(".")
    return text if text not in ("-0", "") else "0"


def style(coerced: pd.DataFrame, types: dict[str, str], mask: pd.DataFrame):
    """천 단위 구분·소수 넷째 자리까지, 결측 셀 하이라이트."""
    formats = {}
    for column, kind in types.items():
        if kind == "int":
            formats[column] = "{:,}"
        elif kind == "float":
            formats[column] = _fmt_float
    styler = coerced.style.format(formats, na_rep="")
    css = np.where(mask.to_numpy(), NULL_STYLE, "")
    return styler.apply(lambda _: css, axis=None)


def _top(values: list[str], k: int = 3) -> str:
    counts = pd.Series(values, dtype=object).value_counts().head(k)
    return ", ".join(f"{_clip(v)} ({n})" for v, n in counts.items())


def _clip(value: str, width: int = 24) -> str:
    return value if len(value) <= width else value[: width - 1] + "…"


def summarize(frame: pd.DataFrame, coerced: pd.DataFrame, types: dict[str, str]) -> pd.DataFrame:
    """컬럼마다 한 줄. 표시용이라 값은 전부 문자열로 만든다."""
    total = len(frame)
    records = []
    for column in data_columns(frame):
        kind = types[column]
        values = _non_null(frame[column])
        rec = {
            "컬럼": column, "타입": kind, "값 있음": len(values),
            "결측 %": f"{(total - len(values)) / total:.1%}" if total else "-",
            "최소": "", "최대": "", "평균": "", "고유값": len(set(values)),
            "상위 값": _top(values) if values else "", "메모": "",
        }
        if kind in ("int", "float") and values:
            series = coerced[column].dropna().astype(float)
            fmt = (lambda x: f"{int(x):,}") if kind == "int" else _fmt_float
            rec.update({"최소": fmt(series.min()), "최대": fmt(series.max()),
                        "평균": _fmt_float(series.mean())})
        elif kind == "datetime" and values:
            series = coerced[column].dropna()
            rec.update({"최소": str(series.min()), "최대": str(series.max())})
        elif kind == "str" and values:
            numeric = sum(1 for v in values if _FLOAT.fullmatch(v))
            if numeric >= 0.8 * len(values):
                rec["메모"] = f"숫자처럼 보이지만 {len(values) - numeric}개 실패"
        records.append(rec)
    return pd.DataFrame(records)


def chart_data(frame: pd.DataFrame, coerced: pd.DataFrame, types: dict[str, str],
               column: str) -> tuple[str, pd.DataFrame]:
    """("bar" | "line", 차트용 데이터). 데이터가 없으면 빈 DataFrame."""
    kind = types[column]
    if kind in ("int", "float"):
        series = coerced[column].dropna().astype(float).to_numpy()
        if series.size == 0:
            return "bar", pd.DataFrame()
        bins = max(1, min(20, len(np.unique(series))))
        counts, edges = np.histogram(series, bins=bins)
        labels = [f"{_fmt_float(a)} – {_fmt_float(b)}" for a, b in zip(edges[:-1], edges[1:])]
        return "bar", pd.DataFrame({"개수": counts}, index=pd.Index(labels, name=column))
    if kind == "datetime":
        series = coerced[column].dropna()
        if series.empty:
            return "line", pd.DataFrame()
        days = series.dt.floor("D")
        bucket = days if days.nunique() <= 60 else series.dt.to_period("M").dt.to_timestamp()
        counts = bucket.value_counts().sort_index()
        return "line", pd.DataFrame({"개수": counts.to_numpy()},
                                    index=pd.Index(counts.index, name=column))
    values = _non_null(frame[column])
    counts = pd.Series(values, dtype=object).value_counts().head(10)
    return "bar", pd.DataFrame({"개수": counts.to_numpy()},
                               index=pd.Index([_clip(v) for v in counts.index], name=column))


def page_warnings(frame: pd.DataFrame) -> dict[str, int]:
    """열 수가 어긋난 행 수, 디코딩 대체 문자 수.

    디코딩 오류는 U+FFFD 개수로 센다. 원본에 그 문자가 실제로 들어 있으면 그만큼
    많이 세는 근사다.
    """
    ragged = int(frame[FLAG].notna().sum()) if FLAG in frame else 0
    decode = sum(v.count("�") for c in frame.columns for v in frame[c] if isinstance(v, str))
    return {"ragged_rows": ragged, "decode_errors": decode}
