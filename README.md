# CSV Viewer

큰 CSV 파일을 **전부 읽지 않고** 페이지 단위(기본 100행)로 빠르게 훑어보는 Streamlit 뷰어.

- 1GB 파일도 첫 페이지가 수 ms 안에 뜬다 — 헤더 바로 뒤에서 100행만 읽는다
- 나머지 페이지는 백그라운드 인덱싱이 행 시작 위치를 채워 가는 만큼 바로 이동할 수 있다
- 타입별 숫자 포맷, 결측 하이라이트, 컬럼 요약·차트 (현재 페이지 기준)

같은 저장소에 표준 라이브러리만 쓰는 배치 검증 CLI(`src/run.py`)도 있다 — 뷰어와 독립적이다.

---

## 빠른 시작

요구사항: **Python 3.14**

```bash
git clone https://github.com/junholeephy/csv_viewer.git
cd csv_viewer

python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

streamlit run src/app.py
```

브라우저에서 **http://localhost:8501** 을 연다. 보고 싶은 파일은 **`./csv_files/`** 에 넣는다
(처음 실행하면 폴더가 만들어진다). 넣은 뒤 브라우저를 새로고침하면 사이드바 목록에 뜬다.

- `csv_files/` 아래의 `.csv` `.tsv` `.txt` 가 하위 폴더까지 목록에 뜬다. 이 폴더는 `.gitignore` 에 있어 커밋되지 않는다
- 상대 경로는 **실행한 위치(cwd) 기준**이다 — 저장소 루트에서 실행하면 `<저장소>/csv_files`
- 다른 폴더를 보려면: `streamlit run src/app.py -- --root <폴더>` (`--` 뒤는 앱에 넘기는 인자)
- 접속은 **이 컴퓨터에서만**(localhost) 된다. `.streamlit/config.toml` 이 묶어 두며, 이 파일도 cwd 기준으로
  읽힌다. 다른 위치에서 실행할 때는 `--server.address localhost` 를 붙인다
- 포트 변경: `streamlit run src/app.py --server.port 8502`. 끄려면 `Ctrl+C`

## 화면

```
+--------------------------------------------------------------+
| 사이드바                 | 본문                              |
|  파일 선택               |  파일 이름, 크기, 인코딩, 구분자  |
|  인코딩 (자동 감지)      |  인덱싱 진행 바 -> 전체 n행       |
|  구분자 (자동 감지)      |  [처음][이전][페이지][다음][끝]   |
|  페이지 크기 50/100/500  |  경고 (열 수 불일치, 디코딩 오류) |
|  원본 보기               |  탭: [표] [컬럼 요약]             |
+--------------------------------------------------------------+
```

- **표**: 행 번호는 원본 데이터 행 기준(1부터). 숫자는 천 단위 구분·소수 넷째 자리까지, 결측 셀은 주황색.
  열 머리글을 클릭하면 **현재 페이지 안에서** 정렬된다. 긴 문자열은 셀을 더블클릭하면 전체가 보인다
- **컬럼 요약**: 컬럼별 타입·결측률·최소/최대/평균·고유값·상위 값, 선택한 컬럼의 차트
- **원본 보기**: 타입 변환·포맷 없이 파일의 문자열 그대로
- **끝** 버튼은 인덱싱이 끝나야 열린다. 아직 인덱싱되지 않은 페이지로 가려 하면 안내가 뜬다

### 읽는 규칙

| 항목 | 동작 |
|---|---|
| 구분자 | `,` `탭` `;` `\|` 중 앞부분 샘플로 자동 감지 (사이드바에서 변경 가능) |
| 인코딩 | UTF-8(BOM 포함) → CP949 순으로 시도, 둘 다 아니면 latin-1. EUC-KR 도 선택 가능 |
| 헤더 | 첫 번째 비어 있지 않은 행. 빈 이름은 `col_<n>`, 중복은 `name.1` `name.2` |
| 따옴표 | RFC 4180 — 따옴표 안의 줄바꿈·구분자는 데이터, `""` 는 따옴표 하나 |
| 빈 줄 | 행으로 세지 않는다 |
| 열 수 불일치 | 모자라면 빈칸, 넘치면 `…extra` 열에 모은다. `⚠` 열에 "열 실제/기대" 표시 |
| 결측 | `""` `NA` `N/A` `null` `NULL` `None` `-` |
| 타입 | 페이지의 비결측 값이 **전부** 해석될 때만 int → float → bool → datetime(ISO 8601). 하나라도 어긋나면 문자열로 둔다 |
| 잘못된 바이트 | `�` 로 바꿔 보여주고 경고 — 인코딩을 바꿔 보라는 신호 |

## 어떻게 빠른가

pandas `read_csv(skiprows=…)` 로 페이지를 읽으면 뒤쪽 페이지일수록 앞부분을 매번 다시 파싱한다 (비용 ∝ 페이지 위치).
이 뷰어는 대신 **행이 시작하는 바이트 위치(오프셋)** 를 기록해 두고 `seek` 한 번으로 해당 페이지로 건너뛴다.

1. **첫 페이지** — 헤더를 읽으면 첫 데이터 행의 오프셋을 안다. 거기서 100행만 파싱 → 인덱스 불필요
2. **백그라운드 인덱싱** — 스레드가 파일을 한 번 훑으며 50행마다 오프셋(체크포인트)을 남긴다.
   페이지 크기 50/100/500 이 모두 50의 배수라, 어느 페이지든 시작 행이 체크포인트와 정확히 맞는다
3. **행 경계 판정** — 파일을 바이너리로 읽으며 따옴표 상태를 추적하는 상태 기계로 행 끝을 찾는다.
   구분자·따옴표·CR·LF 는 ASCII 이고 UTF-8·CP949 의 멀티바이트 문자 안에 나타나지 않아 디코딩 없이 판정할 수 있다.
   따옴표가 없는 줄은 LF 만 찾아 건너뛰므로 빠르다. 결과는 Python `csv.reader` 와 같은 행 경계가 되도록
   property-based test 로 검증한다
4. **캐시** — Streamlit 은 상호작용마다 스크립트를 다시 실행한다. 인덱싱 작업은
   (경로, 수정 시각, 크기, 인코딩, 구분자) 를 키로 `st.cache_resource` 에 살려 둔다. 파일이 바뀌면 새로 인덱싱한다

### 성능 (1GB, Apple Silicon, 로컬 SSD)

| | 따옴표 없음 (18.2M행) | 행마다 따옴표+줄바꿈 (13.1M행) |
|---|---|---|
| 첫 페이지 | 9 ms | 7 ms |
| 임의 페이지 (500행) | ≤ 2 ms | ≤ 1 ms |
| 인덱싱 | 427 MB/s (2.4 s) | 40 MB/s (26 s) |

```bash
python tools/bench_viewer.py --mb 1024    # 임시 폴더에 합성 파일을 만들어 측정하고 지운다
```

## 한계

- 줄바꿈이 CR 하나뿐인 파일(구형 Mac), UTF-16/32 파일은 지원하지 않는다
- 타입 추론·요약·차트는 **현재 페이지만** 본다 — 파일 전체 통계가 아니다
- 정렬·필터도 현재 페이지 안에서만
- 긴 문자열은 표 셀에 앞부분만 보이고, 페이지의 모든 문자열이 브라우저로 전송된다
  (긴 본문 500행 페이지 ≈ 15MB)
- 디코딩 오류 건수는 `�` 개수로 센다 — 원본에 그 문자가 실제로 있으면 그만큼 많이 센다

---

## 개발

```bash
pip install -r requirements.txt
pip install pytest==9.1.1 hypothesis==6.168.3
python -m pytest -q
```

- 예제 테스트와 property-based test(Hypothesis)를 파일로 나눠 둔다 (`test_*_pbt.py`)
- PBT 가 실패하면 재현 blob 이 출력된다. 같은 입력으로 다시: `pytest --hypothesis-seed=<n>`,
  결정적 실행: `HYPOTHESIS_PROFILE=ci pytest`
- `tests/test_app.py` 는 Streamlit `AppTest` 로 실제 스크립트를 브라우저 없이 돌린다
- 데이터 파일은 커밋하지 않는다 (`.gitignore` 가 `*.csv` 등을 막는다). 테스트 데이터는 코드로 생성한다

### 구조

```
src/
  app.py                  Streamlit 화면 (위젯·세션 상태만). 기본 데이터 폴더 ./csv_files
  run.py                  배치 검증 CLI 진입점 (표준 라이브러리만)
  core/
    load.py               입력 포맷을 아는 유일한 곳 — 구분자 감지, 행 경계 스캐너, 페이지 읽기
    viewer/
      jobs.py             백그라운드 인덱싱 (IndexJob)
      present.py          표 변환·타입 추론·요약·차트 데이터 (pandas)
      files.py            --root 아래 파일 목록, 루트 밖 경로 차단
    schema.py ...         배치 CLI (스키마 검증·리포트)
tests/                    예제 + PBT + AppTest
tools/bench_viewer.py     성능 측정 (개발 전용)
.streamlit/config.toml    localhost 바인딩, 사용 통계 끔
csv_files/                볼 파일을 넣는 곳 (커밋 안 됨)
aidlc-docs/               요구사항·설계·테스트 기록 (AI-DLC)
```

`app → viewer → load/schema` 한 방향으로만 의존한다. 배치 CLI 는 뷰어를 import 하지 않으므로
streamlit·pandas 가 없는 파이썬에서도 돈다.

### 다른 환경으로 배포

이 저장소는 `scripts/sync.sh` 로 태그 단위 사본을 다른 작업 폴더에 풀어 쓰는 구조다
(자세한 규칙은 [`SCAFFOLD.md`](SCAFFOLD.md), [`IMPLEMENTATION_SPEC.md`](IMPLEMENTATION_SPEC.md)).

```bash
# 개발 쪽 — 태그를 내고 사본에 들어갈 내용을 점검한 뒤 push
git tag v0.2
bash scripts/sync.sh v0.2
git push origin main v0.2

# 받는 쪽 — 작업 폴더(예: aaa) 루트에서
git clone https://github.com/junholeephy/csv_viewer.git .staging/csv_viewer   # 최초 1회
bash .staging/csv_viewer/scripts/sync.sh v0.2                                 # 최초·갱신 동일

source <venv>/bin/activate
pip install -r csv_viewer/requirements.txt
streamlit run csv_viewer/src/app.py --server.address localhost   # aaa/csv_files 를 본다
```

- 사본(`aaa/csv_viewer/`)에는 실행에 필요한 코드·테스트·`TODO.md` 만 들어간다.
  `.git`, 개발 문서, `tools/`, `aidlc-docs/` 는 빠진다
- 뷰어는 `configs/env.yaml` 의 `paths.venv` 로 갈아타지 않는다 — venv 를 직접 켠다
- 받는 쪽은 cwd 가 작업 폴더라 사본 안의 `.streamlit/config.toml` 이 읽히지 않는다 —
  `--server.address localhost` 를 직접 붙인다. 데이터는 `aaa/csv_files/` 에 둔다
- 받는 쪽에서 할 일은 사본의 `TODO.md` 에 있다

## 버전

| 태그 | 내용 |
|---|---|
| `v0.1` | 첫 공개 — 페이지 단위 뷰어, 백그라운드 인덱싱, 컬럼 요약 |
| `v0.2` | `streamlit run src/app.py` 만으로 실행 — 기본 데이터 폴더 `./csv_files`, localhost 바인딩 설정 파일, README |
