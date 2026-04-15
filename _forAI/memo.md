# Memo

## 제품 기준선

- 현재 패키지 버전은 `0.1.0`이다.
- Python 요구 버전은 `>=3.11`이고, 패키지 관리는 `uv` 기준이다.
- 런타임 의존성은 `playwright`, `pyyaml` 두 개다.
- 브라우저 바이너리는 패키지 설치와 별도로 `uv run playwright install firefox`가 필요하다.

## 기본 설정값

- ex01, ex02, ex03 모두 `BrowserSessionConfig(headed=True, slow_mo=0, timeout_ms=5000.0)`를 사용한다.
- 공통 프롬프트 문자열은 `browser> `다.
- ex02/ex03의 기본 시스템 파일은 `.playwright/system.yaml`이다.
- `.playwright/system.yaml`이 없고 레거시 `temp/system.yaml`만 있으면 그 파일을 fallback으로 사용한다.
- 스크린샷, DOM dump, YAML 추출, 다운로드 파일은 상대 경로일 때 `.playwright/` 아래로 정리된다.

## 런타임 구조 메모

- `browser.py`가 명령 파싱과 Playwright 세션 관리를 모두 담당하고, ex01~ex03은 REPL 제어층만 추가한다.
- ex01은 순수 브라우저 명령 REPL이다.
- ex02는 ex01 위에 `macro <name>` 실행과 `--system` 인자 처리를 얹는다.
- ex03은 ex02 위에 `tasks`, `task <name|number>`, `wait_for`, `wait_for_navigation`, `on_fail` 정책을 얹는다.
- 루트 `main.py`는 editable install 없이 `src/`를 `sys.path`에 넣은 뒤 ex01 또는 `--ex02`만 호출한다.
- 패키지 `__main__.py`는 ex01만 실행한다.

## 동작 규칙

- 페이지 전체 전환이 핵심이면 `wait_for_navigation`, 특정 DOM 준비가 핵심이면 `wait_for`를 우선한다.
- 민감한 입력은 출력 시 `type`, `fill` 명령의 마지막 인자를 `<hidden>`으로 숨긴다.
- 현재 새 창 감지는 클릭 뒤 최대 1.5초 동안 새 `Page`가 생기는지 폴링하는 방식이다.
- `download_links`와 `save_yaml`은 실습 상세 페이지 같은 반구조화 화면에서 데이터를 수집하는 데 초점을 둔다.

## 열린 이슈

- `click()`의 새 페이지 감지는 현재 최대 1.5초 동안 폴링하므로 늦게 뜨는 팝업은 놓칠 수 있다.
- `wait_for_selector` 기본 timeout은 5초라서 사이트별 로딩 편차가 크면 step별 override가 필요할 수 있다.
- REPL 입력 제어와 브라우저 명령 파싱에 대한 자동화 테스트가 아직 없다.

## 반복 금지

- 실제 저장소 경로가 바뀌었는데 `_forAI` 문서 경로를 예전 값으로 유지하지 않는다.
- 참고 정보와 남은 작업을 섞지 않는다. 구현 사실은 `memo.md`, 앞으로 할 일은 `plan.md`에 둔다.
- `.playwright/`로 옮긴 산출물 경로를 다시 범용 `temp/` 문맥으로 설명하지 않는다.
