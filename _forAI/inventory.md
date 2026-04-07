# Inventory

## Repository

- Name: `playwrite_tutorial`
- Path: `/Volumes/data/work/aiwork/python_study/playwrite_tutorial`

## Top-level structure

- `src/playwrite_tutorial/`: REPL 예제와 Firefox 제어 로직이 들어 있는 메인 패키지
- `.playwright/`: 매크로/태스크 정의, DOM dump, screenshot 같은 로컬 Playwright 산출물
- `.playwright-cli/`: Playwright CLI가 남긴 로컬 로그와 페이지 스냅샷
- `_forAI/`: AI 작업용 계획, 인벤토리, 메모, 변경 기록 문서
- `.venv/`: `uv`가 만든 로컬 가상환경
- `README.md`: 설치/실행 방법과 명령 예제
- `main.py`: `src/` 패키지를 호출하는 얇은 진입점
- `pyproject.toml`: 프로젝트 메타데이터, 의존성, REPL 스크립트 정의
- `uv.lock`: `uv`가 생성한 잠금 파일

## Entrypoints

- `uv run ex01_repl`
- `uv run ex02_macro`
- `uv run ex03_tasks`
- `uv run python main.py`
- `playwrite_tutorial.ex01:main`
- `playwrite_tutorial.ex02:main`
- `playwrite_tutorial.ex03:main`

## Tests

- 자동화 테스트 디렉터리는 아직 없다.
- 현재 검증 방식은 REPL 진입과 실제 브라우저 실행 확인이다.
- Playwright 명령 파싱과 REPL 입력 레이어가 커지면 `tests/` 디렉터리와 단위 테스트를 추가할 필요가 있다.

## Notes

- 런타임 의존성은 현재 `playwright`, `pyyaml`이다.
- Firefox 사용 전 `uv run playwright install firefox`를 따로 실행해야 한다.
- 현재 구조는 "단일 세션 + 순차 명령 실행" REPL에 초점을 둔다.
- ex02/ex03의 기본 설정 파일은 `.playwright/system.yaml`이며, 필요하면 `--system`으로 다른 파일을 지정할 수 있다.
