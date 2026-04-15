# Inventory

## Repository

- Name: `playwrite_tutorial`
- Path: `/Volumes/data/work/aiwork/playwrite_tutorial`
- Summary: `uv` 기반 Playwright 학습 저장소로, Firefox REPL(ex01), YAML 매크로(ex02), 스마트 태스크(ex03)를 단계적으로 익히는 예제를 제공한다.

## Top-level structure

- `src/playwrite_tutorial/`: 공통 브라우저 세션과 ex01~ex03 실행 로직이 들어 있는 메인 패키지
- `src/playwrite_tutorial/browser.py`: Playwright Firefox 세션, 명령 파싱, DOM 저장, 스크린샷, YAML 추출, 링크 다운로드를 담당한다.
- `src/playwrite_tutorial/macros.py`: `.playwright/system.yaml`과 레거시 `temp/system.yaml` 사이의 시스템 파일 fallback을 관리한다.
- `src/playwrite_tutorial/ex01.py`: 기본 REPL 예제다.
- `src/playwrite_tutorial/ex02.py`: YAML 기반 매크로 REPL 예제다.
- `src/playwrite_tutorial/ex03.py`: step별 대기 조건과 실패 정책을 갖는 태스크 러너다.
- `.playwright/`: 매크로/태스크 정의, DOM dump, screenshot, YAML 추출, 다운로드 같은 로컬 Playwright 산출물 경로다.
- `.playwright-cli/`: Playwright CLI가 남긴 로컬 로그와 페이지 스냅샷이다.
- `_forAI/`: AI 작업용 문서 세트다.
- `README.md`: 설치, 실행 예제, 지원 명령, `.playwright/` 산출물 규칙을 설명한다.
- `main.py`: editable install 없이 `src/`를 경로에 넣고 ex01 또는 `--ex02`를 실행하는 얇은 래퍼다.
- `forai-scaffold.skill`: `_forAI` 문서 세트를 정리할 때 참조하는 로컬 스킬 파일이다.
- `pyproject.toml`: 의존성, Python 요구 버전, console script 엔트리포인트를 정의한다.
- `uv.lock`: `uv` 잠금 파일이다.

## Entrypoints and key modules

- `uv run ex01_repl`: 기본 Firefox REPL을 실행한다.
- `uv run ex02_macro [--system <path>]`: YAML 매크로 REPL을 실행한다.
- `uv run ex03_tasks [--system <path>]`: 태스크 REPL을 실행한다.
- `uv run python main.py`: 기본은 ex01, `--ex02`를 주면 ex02를 실행한다.
- `uv run python -m playwrite_tutorial`: 패키지 `__main__`을 통해 ex01을 실행한다.
- `playwrite_tutorial.browser.BrowserSession`: 모든 예제가 공유하는 공통 브라우저 세션 레이어다.
- `playwrite_tutorial.macros.get_system_file`: `.playwright/system.yaml` 우선, 없으면 `temp/system.yaml` fallback 규칙을 제공한다.

## Build and validation commands

- `uv sync`: 의존성을 설치한다.
- `uv run playwright install firefox`: Firefox 브라우저 바이너리를 설치한다.
- `uv run ex01_repl`: 기본 명령 REPL 진입을 확인한다.
- `uv run ex02_macro --system .playwright/system.yaml`: 매크로 파일 로딩을 확인한다.
- `uv run ex03_tasks --system .playwright/system.yaml`: 태스크 로딩과 step 실행 경로를 확인한다.
- `uv run python main.py`: 루트 래퍼가 ex01로 연결되는지 확인한다.

## Tests

- 별도 `tests/` 디렉터리는 아직 없다.
- 현재 검증 방식은 콘솔 엔트리포인트 실행, REPL 진입, 실제 Firefox 세션 동작 확인 중심이다.
- `browser.py`의 명령 파서와 ex02/ex03의 REPL 제어 로직은 자동화 테스트가 아직 없어 회귀 검증 공백이 있다.

## Notes

- 런타임 의존성은 현재 `playwright`, `pyyaml`이다.
- Python 요구 버전은 `>=3.11`이다.
- 현재 구조는 "단일 브라우저 세션 + 순차 명령 실행" REPL에 초점을 둔다.
- 새 페이지 감지는 `browser.py`에서 최대 1.5초 폴링으로 처리한다.
- ex02/ex03의 기본 설정 파일은 `.playwright/system.yaml`이며, 필요하면 `--system`으로 다른 파일을 지정할 수 있다.
