# playwrite tutorial

Playwright Python을 `uv` 환경에서 익히기 위한 실습 저장소입니다.

## Setup

```bash
uv sync
uv run playwright install firefox
```

## Examples

### ex01 – 순수 REPL

브라우저를 열고 명령을 한 줄씩 입력하면서 Playwright 기본 동작을 익힌다.
매크로 없이 단순 REPL만 제공한다.

```bash
uv run ex01_repl
```

### ex02 – REPL + 매크로

ex01의 REPL에 YAML 기반 매크로 시스템을 추가한 버전이다.
기본적으로 `.playwright/system.yaml`에서 매크로를 읽는다.

```bash
uv run ex02_macro                          # .playwright/system.yaml 사용
uv run ex02_macro --system my_macros.yaml  # 다른 파일 지정
```

### ex03 – REPL + 스마트 태스크

ex02의 매크로를 업그레이드한 버전이다.
각 단계의 성공/실패를 확인하고, 셀렉터 기반으로 페이지 로딩을 대기한다.

- **`wait_for`**: 고정 `wait` 대신 셀렉터가 나타날 때까지 대기
- **`wait_for_navigation`**: 페이지 전환 완료 대기
- **`on_fail`**: `stop`(중단) / `skip`(건너뜀) / `retry`(재시도)
- **`wait 1 3`**: 1~3초 사이 랜덤 대기 (사람처럼 보이도록)

```bash
uv run ex03_tasks
uv run ex03_tasks --system my_tasks.yaml
```

ex02의 매크로(`macro <name>`)도 그대로 사용 가능하다.

#### main.py로 실행

```bash
uv run python main.py              # ex01 실행
uv run python main.py --ex02       # ex02 실행
```

## .playwright/ 디렉토리

실행 중 생성되는 로컬 파일은 `.playwright/` 아래에 저장된다.

- `.playwright/system.yaml` – 매크로/태스크 정의 파일 (ex02, ex03에서 사용)
- `.playwright/_dom.tmp` – `dom` 명령 결과
- `.playwright/*.png` – `screenshot` 명령 결과 (상대 경로 지정 시)

`.playwright/`는 `.gitignore`에 포함되어 있으므로 커밋되지 않는다.

## 기능 추가 정리

- `ex01`: 기본 브라우저 REPL과 `goto`, `click`, `fill`, `dom`, `screenshot` 같은 직접 제어 명령을 제공한다.
- `ex02`: YAML 기반 매크로를 추가해서 `.playwright/system.yaml`에 정의한 명령 묶음을 `macro <name>`으로 실행할 수 있다.
- `ex03`: 매크로를 스마트 태스크로 확장해서 step별 `wait_for`, `wait_for_navigation`, `on_fail` 정책을 지원한다.
- 번호 실행: `tasks` 명령은 목록을 번호와 함께 보여주고, `task 2`처럼 번호로도 실행할 수 있다.
- `retry`: 무한 반복이 아니라 실패 시 같은 step을 한 번만 더 시도한다.
- `hover <selector>`: hover 기반 드롭다운 메뉴나 툴팁을 다루기 위한 브라우저 명령을 추가했다.
- 저장 경로 정리: 기본 로컬 작업 디렉토리를 `temp/`에서 `.playwright/`로 옮겼다.
- 예제 보강: `.playwright/system.yaml`의 `login_miso` 태스크는 로그인 후 `K크래딧 -> 회차별 배정 인원 확인` 흐름까지 포함한다.

## Supported Commands

- `goto <url>` / `open <url>`: URL로 이동
- `click <selector>`: CSS 또는 Playwright locator selector 클릭
- `hover <selector>`: 요소 위로 마우스를 올려 hover 메뉴나 툴팁 활성화
- `clickables`: 클릭 가능한 요소 후보 요약
- `elements <selector>`: 셀렉터 매칭 요소 요약
- `type <selector> <text>`: 포커스 후 텍스트 입력
- `fill <selector> <text>`: 기존 값을 지우고 새 값으로 채움
- `clear <selector>`: 요소 값 비우기
- `value <selector>`: 입력 요소의 현재 값 읽기
- `save_yaml <path> <label> [label...]`: 현재 페이지에서 라벨 기반으로 값을 추출해 YAML 파일로 저장
- `download_links <selector> [dir]`: selector에 매칭되는 링크를 순서대로 클릭해 첨부 파일 다운로드
- `wait <seconds>`: 지정한 초만큼 대기
- `wait <min> <max>`: min~max초 사이 랜덤 대기
- `screenshot <path>`: 현재 페이지를 파일로 저장 (`.playwright/` 기준)
- `dom`: 현재 페이지 HTML을 `.playwright/_dom.tmp`에 저장
- `title`: 현재 페이지 제목 출력
- `close`: 명령 실행 조기 종료

## Macros (ex02)

`.playwright/system.yaml`에 매크로를 정의한다.

```yaml
macros:
  login_example:
    description: "예시 로그인"
    commands:
      - "goto https://example.com"
      - "fill input[name=id] myid"
      - "fill input[name=pw] mypassword"
      - "click button[type=submit]"
```

REPL에서 실행:

```text
macros              # 매크로 목록 보기
macro login_example # 매크로 실행
```

## Tasks (ex03)

`.playwright/system.yaml`에 태스크를 정의한다.
매크로와 달리 각 step에 대기 조건과 실패 정책을 지정할 수 있다.

```yaml
tasks:
  login_example:
    description: "예시 로그인 (스마트 대기)"
    steps:
      - action: "goto https://example.com"
        wait_for: "input[name=id]"           # 셀렉터가 보일 때까지 대기

      - action: "fill input[name=id] myid"

      - action: "click button[type=submit]"
        wait_for_navigation: true            # 페이지 전환 완료 대기
        on_fail: stop                        # stop / skip / retry

      - action: "wait 1 3"                   # 1~3초 랜덤 대기
```

REPL에서 실행:

```text
tasks              # 태스크 목록 보기
task login_example # 이름으로 태스크 실행
task 2             # 번호로 태스크 실행
```

실습 목록 화면에서는 `.playwright/system.yaml`의 `export_current_practice_page` 태스크로 첫 번째 항목의 상세 페이지를 열고 아래 작업을 한 번에 수행할 수 있다.

- 첫 번째 실습 행 상세 페이지 열기
- 현재 DOM 저장
- `학습자 이름`, `실습내용`, `제출 실습내용`을 `.playwright/extracted/practice_detail.yaml`로 저장
- 첨부 링크를 `.playwright/downloads/practice_detail/` 아래로 다운로드

## Notes

- Firefox 브라우저 바이너리는 `uv run playwright install firefox`로 별도 설치 필요
- 캔버스 기반 게임 화면은 `dom`, `elements`, `clickables`로 내부 UI를 읽기 어렵다
- 이런 화면은 `screenshot` + VLM/VLA 같은 시각 기반 접근이 더 적합하다
