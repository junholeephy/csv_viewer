# Performance Test Instructions

```bash
.venv/bin/python tools/bench_viewer.py --mb 1024     # 임시 디렉터리에 1GB × 2 생성 후 자동 삭제
```

## Result (2026-10-01, Apple Silicon, local SSD, Python 3.14.7)
| | plain (1,024MB, 18.2M행) | quoted (1,024MB, 13.1M행, 행마다 따옴표+줄바꿈) | Target |
|---|---|---|---|
| P-1 첫 페이지 | 9.1 ms | 7.2 ms | ≤ 1000 ms |
| P-2 임의 페이지(500행, 20회 최대) | 1.6 ms | 0.5 ms | ≤ 300 ms |
| P-3 인덱싱 처리량 | 426.7 MB/s (2.4s) | 39.7 MB/s (25.8s) | ≥ 50 / ≥ 10 MB/s |

모두 충족. quoted 는 모든 행이 느린 경로(바이트 단위 상태 기계)를 타는 최악에 가까운 경우.
