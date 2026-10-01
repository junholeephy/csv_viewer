"""백그라운드 인덱싱.

파일을 한 번 훑으며 STRIDE 행마다 행 시작 오프셋(체크포인트)을 남긴다. 페이지 크기
50/100/500 이 모두 STRIDE 의 배수라, 어느 페이지든 시작 행이 체크포인트와 정확히
맞는다 — 페이지 이동은 seek 한 번이다.

Streamlit 을 모른다. 재실행 사이에 살려두는 것(캐싱)은 화면 쪽 책임이다.
"""

import os
import threading
from dataclasses import dataclass

from ..load import CsvFormat, iter_row_offsets

STRIDE = 50
_PUBLISH_EVERY = 5_000           # 이만큼 행을 볼 때마다 진행 상황을 내보낸다


@dataclass(frozen=True)
class IndexProgress:
    rows_seen: int
    bytes_done: int
    total_bytes: int
    done: bool
    error: str | None


class IndexJob:
    def __init__(self, path: str, fmt: CsvFormat, data_start: int, stride: int = STRIDE) -> None:
        self.path, self.fmt, self.data_start, self.stride = path, fmt, data_start, stride
        self.total_bytes = os.path.getsize(path)
        self._checkpoints: list[int] = []
        self._rows = 0
        self._bytes = data_start
        self._done = False
        self._error: str | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, daemon=True,
                                                name=f"index:{os.path.basename(self.path)}")
                self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    @property
    def abandoned(self) -> bool:
        """멈췄는데 끝나지 않았다 — 다시 쓰려면 새로 만들어야 한다."""
        with self._lock:
            return self._stop.is_set() and not self._done

    def progress(self) -> IndexProgress:
        with self._lock:
            return IndexProgress(self._rows, self._bytes, self.total_bytes, self._done, self._error)

    def offset_of_row(self, row: int) -> int | None:
        """row(0-based 데이터 행, stride 의 배수)가 시작하는 오프셋. 아직 모르면 None."""
        if row % self.stride:
            raise ValueError(f"row {row} 는 stride {self.stride} 의 배수가 아니다")
        if row == 0:
            return self.data_start                    # 첫 페이지는 인덱스 없이 열린다
        index = row // self.stride
        with self._lock:
            return self._checkpoints[index] if index < len(self._checkpoints) else None

    def last_reachable_page(self, page_size: int) -> int:
        """지금 이동할 수 있는 마지막 페이지(0-based). 페이지 0 은 인덱스 없이도 열린다."""
        with self._lock:
            if self._done:
                return max(0, -(-self._rows // page_size) - 1)
            known = len(self._checkpoints)
        return max(0, (known - 1) * self.stride // page_size) if known else 0

    def _publish(self, pending: list[int], rows: int, bytes_done: int, done: bool = False) -> None:
        with self._lock:
            self._checkpoints.extend(pending)
            self._rows, self._bytes, self._done = rows, bytes_done, done
        pending.clear()

    def _run(self) -> None:
        rows, pending = 0, []
        try:
            for offset in iter_row_offsets(self.path, self.fmt, self.data_start):
                if rows % self.stride == 0:
                    pending.append(offset)
                rows += 1
                if rows % _PUBLISH_EVERY == 0:
                    self._publish(pending, rows, offset)
                    if self._stop.is_set():
                        return
            self._publish(pending, rows, self.total_bytes, done=True)
        except Exception as exc:  # 스레드 밖으로 못 나가므로 화면이 볼 수 있게 남긴다
            # 여기까지 찾은 체크포인트는 살린다 — 그 범위 안의 페이지는 계속 열 수 있다
            self._publish(pending, rows, self._bytes, done=True)
            with self._lock:
                self._error = f"{type(exc).__name__}: {exc}"
