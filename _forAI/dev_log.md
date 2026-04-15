# Dev Log

## Entries

- 2026-04-15: `forai-scaffold` 기준으로 `_forAI` 문서를 실제 워크스페이스(`/Volumes/data/work/aiwork/playwrite_tutorial`)와 동기화했고, 실행 엔트리포인트, 검증 명령, 런타임 기본값, 레거시 시스템 파일 fallback, 테스트 공백을 문서에 반영했다.
- 2026-04-07: 직접 파일 URL 첨부는 Playwright download 이벤트 대신 현재 브라우저 세션 쿠키로 URL 저장 fallback을 쓰도록 `download_links`를 보강했고, `save_yaml`은 `학습자` 같은 라벨 별칭도 찾도록 확장했다.
- 2026-04-07: `export_current_practice_page` 태스크를 목록 화면 기준으로 조정해 첫 번째 실습 상세를 연 뒤 YAML 추출과 첨부 다운로드를 시도하도록 바꿨고, `download_links`는 non-download 링크를 만나면 건너뛰도록 보강했다.
- 2026-04-07: 현재 페이지에서 라벨 기반 값 추출을 YAML로 저장하는 `save_yaml` 명령과 첨부 링크를 내려받는 `download_links` 명령을 추가하고, 실습 상세 페이지용 export task를 정의했다.
- 2026-04-07: hover 기반 드롭다운 메뉴를 안정적으로 다루기 위해 `hover <selector>` 브라우저 명령을 추가하고, `login_miso` 태스크를 `K크래딧` hover 흐름으로 보강했다.
- 2026-04-07: ex03의 `tasks` 목록을 번호와 함께 출력하고, `task <number>` 형식으로도 태스크를 실행할 수 있게 정리했다.
- 최신 항목이 위에 오도록 기록한다.
- 2026-04-06: `temp/`에 흩어져 있던 기본 시스템 파일, DOM dump, screenshot 경로를 `.playwright/` 기준으로 정리했다.
- 2026-04-06: ex03의 `wait_for`, `wait_for_navigation`, `wait_for_selector` 블로킹 동작과 AJAX 활용성, 팝업 감지 1.5초 폴링 한계를 `_forAI` 문서에 정리했다.
- 2026-04-04: `dom` 명령을 `_dom.tmp` 저장 방식으로 바꾸고, OS 클립보드 의존을 제거했다.
- 2026-04-04: `clickables`, `elements`, `value`, `fill`, `clear`를 활용해 실제 로그인 폼과 버튼 셀렉터를 점검했다.
- 2026-04-04: 게임 벤더 진입 시 새 창이 늦게 뜨는 케이스를 추적하도록 브라우저 세션을 보강했다.
- 2026-04-04: Evolution은 로더 페이지와 iframe 진입까지 확인했지만, 일부 요청에서 `Access Denied`가 발생할 수 있음을 확인했다.
- 2026-04-04: Dream Game은 게임방 진입까지 확인했으며, 실제 게임 UI가 캔버스 기반이라 DOM 추출보다는 스크린샷 기반 해석이 적합하다는 결론을 정리했다.
- 2026-04-03: `_forAI/` 기본 문서를 생성하고, Playwright + Firefox CLI 예제 구현을 위한 초기 계획을 정리했다.
- 2026-04-03: `uv add playwright`로 의존성을 추가하고, `src/playwrite_tutorial/` 기반 CLI 초안을 구현했다.
- 2026-04-03: `uv run playwright install firefox` 후 `goto`, `title`, `screenshot`, `close` 흐름을 실제 Firefox headless 실행으로 검증했다.
- 2026-04-03: 배치형 CLI 진입점을 정리하고, 프로젝트 기본 흐름을 REPL 중심 학습 예제로 통일했다.
- 2026-04-03: 마지막 접속 URL을 `.playwrite_ex01_history.json`에 저장하고, REPL 시작 시 자동 복원하는 히스토리 기능을 추가했다.
- 2026-04-03: `system.json` 기반 매크로 로더와 `macro <name>` 실행 기능을 추가하고, 출력 시 `type`/`fill` 입력값을 숨기도록 정리했다.
- 2026-04-03: REPL에서 히스토리 저장/복원 기능을 제거하고, 브라우저 조작과 매크로 실행에만 집중하도록 단순화했다.
