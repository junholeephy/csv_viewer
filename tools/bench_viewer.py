"""뷰어 성능 측정 (개발 전용, 배포 대상 아님).

    python tools/bench_viewer.py [--mb 1024] [--keep]

임시 디렉터리에 합성 CSV 두 벌(따옴표 없음 / 따옴표·줄바꿈 많음)을 만들고 측정한다.
  P-1 첫 페이지 준비 (sniff + header + read_rows)    목표 ≤ 1s
  P-2 인덱스된 임의 페이지 read_rows (500행)          목표 ≤ 300ms
  P-3 인덱싱 처리량                                   목표 ≥ 50MB/s (plain), ≥ 10MB/s (quoted)
"""

import argparse
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core import load  # noqa: E402
from core.viewer import jobs  # noqa: E402

HEADER = "id,name,amount,category,created_at,memo\n"


def make_plain(i: int) -> str:
    return f"{i},user_{i:08d},{i * 1.37:.2f},{'ABC'[i % 3]},2024-01-{i % 28 + 1:02d}T10:00:00,ok\n"


def make_quoted(i: int) -> str:
    return (f'{i},"Kim, {i}",{i * 1.37:.2f},"{"ABC"[i % 3]}",2024-01-{i % 28 + 1:02d},'
            f'"line one\nline ""two"" {i}"\n')


def generate(path: Path, row: callable, target_bytes: int) -> int:
    rows, written = 0, 0
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(HEADER)
        while written < target_bytes:
            block = "".join(row(rows + k) for k in range(10_000))
            fh.write(block)
            written += len(block)
            rows += 10_000
    return rows


def bench(path: Path, label: str, target_rate: float) -> None:
    size = path.stat().st_size
    t0 = time.perf_counter()
    fmt = load.sniff_format(str(path))
    columns, data_start = load.read_header(str(path), fmt)
    first = load.read_rows(str(path), fmt, data_start, 100)
    p1 = time.perf_counter() - t0

    t0 = time.perf_counter()
    job = jobs.IndexJob(str(path), fmt, data_start)
    job.start()
    job.join()
    p3_s = time.perf_counter() - t0
    progress = job.progress()

    rng = random.Random(0)
    last = job.last_reachable_page(500)
    samples = []
    for _ in range(20):
        page = rng.randint(0, last)
        t0 = time.perf_counter()
        load.read_rows(str(path), fmt, job.offset_of_row(page * 500), 500)
        samples.append(time.perf_counter() - t0)
    p2 = max(samples)

    rate = size / 2**20 / p3_s
    print(f"[{label}] {size / 2**20:,.0f} MB, {progress.rows_seen:,} rows, {len(columns)} cols")
    print(f"  P-1 first page : {p1 * 1000:8.1f} ms  {'OK' if p1 <= 1 else 'MISS'} (≤ 1000 ms, {len(first)} rows)")
    print(f"  P-2 random page: {p2 * 1000:8.1f} ms  {'OK' if p2 <= 0.3 else 'MISS'} (max of 20, ≤ 300 ms)")
    print(f"  P-3 indexing   : {rate:8.1f} MB/s {'OK' if rate >= target_rate else 'MISS'} "
          f"(≥ {target_rate:.0f} MB/s, {p3_s:.1f}s)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mb", type=int, default=1024, help="파일당 크기 (MB)")
    ap.add_argument("--keep", action="store_true", help="생성한 파일을 지우지 않는다")
    args = ap.parse_args()

    workdir = Path(tempfile.mkdtemp(prefix="bench_viewer_"))
    try:
        for label, row, rate in (("plain", make_plain, 50), ("quoted", make_quoted, 10)):
            path = workdir / f"{label}.csv"
            t0 = time.perf_counter()
            generate(path, row, args.mb * 2**20)
            print(f"generated {path} in {time.perf_counter() - t0:.1f}s")
            bench(path, label, rate)
    finally:
        if args.keep:
            print(f"kept: {workdir}")
        else:
            shutil.rmtree(workdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
