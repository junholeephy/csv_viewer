# Components — csv-viewer

| ID | Component | Location | Streamlit 의존 |
|---|---|---|---|
| C1 | Paged CSV Reader | `src/core/load.py` (확장) | No |
| C2 | Index Job | `src/core/viewer/jobs.py` | No |
| C3 | Presenter | `src/core/viewer/present.py` | No (pandas only) |
| C4 | File Catalog | `src/core/viewer/files.py` | No |
| C5 | Viewer App (UI) | `src/app.py` | Yes |
| (재사용) | Schema helpers | `src/core/schema.py` — `NULL_TOKENS`, `is_null` | No |

## C1 Paged CSV Reader
- **Purpose**: 입력 포맷을 아는 유일한 곳 (스캐폴드 원칙 유지). 기존 `load_csv` 는 그대로 둔다.
- **Responsibilities**: 인코딩/구분자 감지, 헤더 읽기, 바이너리 기준 행 시작 오프셋 스캔(따옴표 인지), 오프셋에서 N행 읽기.
- **Interface**: `CsvFormat`, `sniff_format`, `read_header`, `iter_row_offsets`, `read_rows`.

## C2 Index Job
- **Purpose**: 파일 하나에 대한 체크포인트 인덱스를 백그라운드 스레드로 구축하고 진행 상태를 노출.
- **Responsibilities**: C1 의 `iter_row_offsets` 를 소비하며 50행마다 체크포인트 저장, 진행률(바이트·행) 제공, 중단(stop), 오류 보관, 페이지 시작 오프셋 조회.
- **Interface**: `IndexJob(path, fmt, data_start, stride=50)`, `start`, `stop`, `progress`, `offset_of_row`.
- **Note**: Streamlit 을 모른다. 캐싱(`st.cache_resource`)은 C5 의 책임.

## C3 Presenter
- **Purpose**: 원시 행(list[list[str]])을 읽기 좋은 표와 요약으로 변환.
- **Responsibilities**: DataFrame 변환(원본 행 번호 인덱스), 페이지 기준 타입 추론, 타입 변환(숫자 → numeric dtype 으로 우측 정렬), 결측 하이라이트 스타일, 컬럼 요약표, 차트용 시리즈.
- **Interface**: `to_frame`, `infer_types`, `coerce`, `summarize`, `null_mask`.

## C4 File Catalog
- **Purpose**: 루트 디렉터리 하위의 데이터 파일 목록과 경로 제한.
- **Responsibilities**: `*.csv|*.tsv|*.txt` 재귀 목록(상대 경로), 선택 경로가 루트 밖이면 거부.
- **Interface**: `list_data_files`, `resolve_within`.

## C5 Viewer App
- **Purpose**: Streamlit 위젯 배치와 세션 상태만 담당.
- **Responsibilities**: `--root` 인자 파싱, 사이드바(파일·인코딩·구분자·페이지 크기), IndexJob 캐싱(`st.cache_resource`), 진행률 fragment, 페이지 내비게이션, 표/요약/차트 렌더링, 오류 안내.
