# Business Logic Model — csv-viewer

## L1. 행 경계 스캐너 (`iter_row_offsets`) — 핵심 알고리즘

**목표**: 바이너리 모드로 바이트를 한 번 훑으며, Python `csv.reader` (기본 방언: `doublequote=True`, `strict=False`) 와 **같은 행 경계**를 찾는다.

**왜 바이너리인가**: 텍스트 모드 `tell()` 은 바이트 위치가 아닌 불투명 쿠키이고, 디코딩 비용도 든다. 구분자·따옴표·`\r`·`\n` 은 모두 ASCII 이며 UTF-8 과 CP949 에서 멀티바이트 문자의 일부로 나타나지 않으므로(CP949 후행 바이트는 0x41–0xFE) 바이트 단위 판정이 안전하다. UTF-16/32 는 지원하지 않는다.

**상태 기계** (`q` = 따옴표 바이트, `d` = 구분자 바이트):

| 상태 | 입력 | 다음 상태 / 동작 |
|---|---|---|
| `FIELD_START` | `q` | `IN_QUOTED` |
| | `d` | `FIELD_START` (행에 내용 있음 표시) |
| | `\n` | 행 끝 |
| | `\r` | 무시 (CRLF 의 일부) |
| | 기타 | `IN_FIELD` |
| `IN_FIELD` | `d` | `FIELD_START` |
| | `\n` | 행 끝 |
| | `\r` | 무시 |
| | 기타(따옴표 포함) | `IN_FIELD` — 필드 중간의 따옴표는 리터럴 (csv 모듈과 동일) |
| `IN_QUOTED` | `q` | `QUOTE_IN_QUOTED` |
| | 기타(`\n`, `\r`, `d` 포함) | `IN_QUOTED` — 데이터 |
| `QUOTE_IN_QUOTED` | `q` | `IN_QUOTED` (`""` = 이스케이프된 따옴표) |
| | `d` | `FIELD_START` |
| | `\n` | 행 끝 |
| | `\r` | 무시 |
| | 기타 | `IN_FIELD` (닫는 따옴표 뒤 문자는 리터럴로 이어 붙음, csv 모듈과 동일) |

**행 시작/빈 줄 처리**:
- `row_start` = 현재 행이 시작된 바이트 오프셋, `has_content` = 이 행에서 `\r`·`\n` 외의 바이트를 봤는가.
- 행 끝(`\n`)에서: `has_content` 이면 `row_start` 를 yield. 그다음 `row_start = 현재위치+1`, `has_content = False`, 상태 = `FIELD_START`.
- EOF 에서: `has_content` 이면 `row_start` 를 yield (마지막 줄바꿈 없는 행).
- 빈 줄(`\n` 또는 `\r\n` 만 있는 줄)은 yield 하지 않음 → 리더가 `csv.reader` 의 `[]` 를 건너뛰는 규칙과 일치.

**청크 처리**: 1MB 청크로 읽는다. 상태는 청크 경계를 넘어 유지된다. 내부 루프는 바이트 단위 Python 루프 대신 `bytes.find` 계열로 다음 "관심 바이트"(`q`, `d`, `\n`)까지 건너뛰어 속도를 확보한다 (구체 최적화는 Code Generation 에서; 정확성 기준은 위 표).

**진행률**: 스캐너는 소비한 바이트 수를 호출자가 알 수 있게 한다 (예: `(offset, bytes_done)` 를 내거나 진행 콜백). 정확한 시그니처는 Code Generation 에서 확정.

## L2. 헤더 읽기 (`read_header`)
1. BOM 처리: 인코딩이 `utf-8-sig` 이고 파일이 `EF BB BF` 로 시작하면 스캔 시작 = 3, 아니면 0.
2. 스캐너로 첫 오프셋 = `header_offset`, 둘째 오프셋 = `data_start` (없으면 파일 크기).
3. `read_rows(header_offset, 1)` 으로 헤더 필드 파싱 → 이름 정규화(R-H1).
4. 파일이 비었거나 내용 있는 행이 없으면 `columns = []`, `data_start = 파일 크기`.

## L3. 페이지 읽기 (`read_rows`)
1. 바이너리로 열고 `offset` 으로 seek.
2. `io.TextIOWrapper(encoding=fmt.encoding, errors="replace", newline="")` 로 감싸고 `csv.reader(delimiter, quotechar)`.
3. `[]`(빈 줄) 은 건너뛰고 최대 `n` 행 수집.
4. `utf-8-sig` 로 오프셋 > 0 위치에서 열 때 BOM 제거 로직이 끼어들지 않도록, 오프셋 > 0 이면 `utf-8` 로 디코딩한다.

## L4. 페이지 → 오프셋 매핑
- `first_row = page * page_size` (0-based 데이터 행).
- `page == 0` → `data_start` (인덱스 불필요).
- 그 외 → `IndexJob.offset_of_row(first_row)` = `checkpoints[first_row // 50]` (stride 가 page_size 의 약수이므로 항상 정확히 맞음). 아직 없으면 `None`.
- 인덱스 완료 후: `total_rows = rows_seen`, `page_count = max(1, ceil(total_rows / page_size))`.
- 인덱싱 중: `max_reachable_page = (len(checkpoints)*50 - 1) // page_size` 단, 해당 페이지 시작 체크포인트가 존재해야 함.

## L5. IndexJob
- 스레드 본문: `for i, off in enumerate(iter_row_offsets(...)): if i % stride == 0: checkpoints.append(off)`; 주기적으로(예: 1만 행마다 또는 청크마다) lock 하에 `rows_seen`, `bytes_done` 갱신, `stop` 플래그 확인.
- 종료 시 `done = True`. 예외는 `error` 에 메시지로 보관하고 `done = True`.
- 체크포인트 리스트는 append-only. 읽기 측은 lock 하에 길이를 확인한 뒤 인덱싱.

## L6. 구분자 감지 (`sniff_format`)
1. 앞 64KB 를 읽고 인코딩 결정: `encoding` 인자가 있으면 그것. 없으면 `utf-8-sig` 엄격 디코딩(샘플 끝에서 잘린 멀티바이트는 증분 디코더 `final=False` 로 허용) → 실패 시 `cp949` → 실패 시 `latin-1`.
2. 샘플의 마지막 불완전 행을 버리고 최대 50행으로 제한.
3. 후보 `, \t ; |` 각각에 대해 `csv.reader` 로 파싱한 행별 필드 수를 구하고, `mode` (최빈 필드 수) 와 `consistency` (mode 와 같은 행의 비율) 계산.
4. `mode >= 2` 인 후보 중 `(consistency, mode)` 최대를 선택. 동률이면 후보 순서(`,` 우선; 확장자가 `.tsv` 면 `\t` 우선).
5. 모두 `mode < 2` 이면 `,` (단일 컬럼 파일).

## L7. 표 변환과 타입 추론 (C3)
1. `to_frame`: 헤더 폭 `W`. 행 길이 < W → 결측(None) 채움. > W → 초과분을 구분자로 이어 `…extra` 컬럼에. 불일치 행이 하나라도 있으면 `⚠` 컬럼(예: "열 7/5") 추가. 인덱스 = `first_row+1 …`.
2. `infer_types` (컬럼별, 결측 = `schema.is_null`):
   - 비결측 값이 없으면 `empty`.
   - 전부 int 패턴(`^[+-]?\d+$`) → `int`; 전부 float 패턴(`^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$`) → `float`; 전부 `true/false`(대소문자 무시) → `bool`; 전부 `datetime.fromisoformat` 성공 → `datetime`; 아니면 `str`.
   - `str` 인데 비결측의 80% 이상이 float 패턴이면 note = "숫자처럼 보이지만 n개 실패".
3. `coerce`: 타입에 따라 nullable dtype(`Int64`, `Float64`, `boolean`, `datetime64`)으로 변환. 결측 토큰은 `<NA>`. `str` 은 원본 유지.
4. `null_mask`: 원본 문자열 기준 `is_null` 의 불리언 프레임 (하이라이트용).
5. `summarize`: 컬럼별 `type, non_null, null_pct, min, max, mean(숫자만), unique, top(상위 3개 "값 (n)"), note`.

## L8. 차트 데이터
- 숫자형: 비결측 값으로 히스토그램(구간 수 = min(20, unique)) → 막대.
- `str`/`bool`: 상위 10개 값 빈도 → 막대.
- `datetime`: 일 단위 빈도(값이 많으면 월 단위) → 선/막대.
- 모두 **현재 페이지** 기준임을 캡션에 명시.

## Testable Properties (PBT-01)

| ID | Component | Category | Property |
|---|---|---|---|
| TP-1 | C1 `iter_row_offsets` + `read_rows` | **Oracle** | 생성한 테이블을 `csv.writer` 로 쓴 파일에서, 각 오프셋에서 1행 읽은 결과 == `csv.reader` 순차 파싱(빈 줄 제외)의 같은 순번 행 |
| TP-2 | C1 `read_header` + `read_rows` | **Round-trip** (PBT-02) | `csv.writer` 로 (헤더, 행들) 을 쓰고 → `read_header` + `read_rows(data_start, N)` == 원본 (헤더는 정규화가 항등인 이름으로 생성) |
| TP-3 | C1 `iter_row_offsets` | **Invariant** (PBT-03) | 오프셋은 strictly increasing, `0 <= off < file_size`, 개수 == 비어 있지 않은 행 수 |
| TP-4 | C1 + C2 | **Invariant** (PBT-03) | 임의 page_size ∈ {50,100,500}(테스트에서는 작은 stride 로 축소 가능)에 대해 체크포인트로 읽은 모든 페이지를 이어 붙이면 == 전체 데이터 행; 마지막 페이지 외에는 길이 == page_size |
| TP-5 | C2 `IndexJob` | **Oracle** | 완료 후 `checkpoints == list(iter_row_offsets(...))[::stride]`, `rows_seen == 전체 행 수` |
| TP-6 | C3 `to_frame` | **Invariant** (PBT-03) | `len(frame) == len(rows)`, 헤더 컬럼이 순서대로 앞에 존재, 인덱스 == `first_row+1 … first_row+len(rows)` |
| TP-7 | C3 `infer_types` + `coerce` | **Invariant** (PBT-03) | 추론 타입이 `str`/`empty` 가 아니면, 원본에서 비결측인 셀은 변환 후에도 결측이 아니다 (조용한 값 손실 없음) |
| TP-8 | C4 `resolve_within` | **Invariant** (PBT-03) | 임의의 상대/절대/`..` 포함 경로에 대해 반환 경로는 항상 root 하위이거나 `ValueError` |
| — | C1 `sniff_format` | No PBT (example-based) | 필드 안에 다른 후보 구분자가 섞인 생성 데이터에서는 정답 자체가 모호해 성질이 성립하지 않음 → 대표 예제 테스트로 검증 |
| — | C5 app | No PBT | UI 배치. 수동 검증 |

**Generators (PBT-07)**: 재사용 가능한 `csv_tables()` 전략을 테스트 공용 모듈에 둔다 — 컬럼 1–8, 행 0–120, 필드 알파벳 = ASCII 영숫자 + `, ; \t | " \n \r` + 공백 + 한글 음절 일부 + 빈 문자열; 줄 종결자 `\n` / `\r\n`; 인코딩 `utf-8-sig` / `cp949`(cp949 인코딩 가능한 문자만). 단독 CR 종결자는 지원 범위 밖이므로 생성하지 않는다 (R-D1).
