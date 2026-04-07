# Memo

## Version management

- Use `major.minor.patch` versioning.
- Start at `1.0.0`.
- Increase `major` for large structural changes or compatibility-breaking changes.
- Increase `minor` for new features or meaningful improvements.
- Increase `patch` for bug fixes or small changes.
- Record version-by-version changes in `dev_log.md`.

## Open questions

- `click()`의 새 페이지 감지는 현재 최대 1.5초 동안 폴링한다. 늦게 뜨는 팝업은 놓칠 수 있어 `expect_popup()` 계열로 바꿀지 검토가 필요하다.
- `wait_for_selector`의 기본 timeout은 현재 5초다. 실제 사이트별 로딩 편차를 보며 timeout 조정이나 step별 override가 필요한지 확인해야 한다.

## Decision criteria

- 페이지 전체 전환을 확인해야 할 때는 `wait_for_navigation`, AJAX나 SPA처럼 특정 UI가 준비됐는지 확인할 때는 `wait_for`를 우선한다.
- 브라우저 자동화 산출물과 로컬 설정은 범용 `temp/`보다 목적이 드러나는 `.playwright/` 아래에 둔다.
- 서버 부하 관점에서는 50ms 폴링 자체보다 실제 `goto`/`click`/재시도 빈도가 더 중요하므로 retry 정책은 보수적으로 유지한다.

## Short notes

- 학습용 예제는 커맨드라인 인자를 최소화하고, REPL에서 기능을 하나씩 직접 시험하는 흐름을 우선한다.
- 새 창, iframe, 벤더 로더 페이지는 REPL에서 `title`, `dom`, `screenshot`으로 현재 위치를 계속 확인하는 편이 안전하다.
- 캔버스 기반 게임방 화면은 DOM보다 스크린샷과 VLM/VLA 접근이 더 현실적이다.
- `ex02`는 로그인 자동화보다 "수동 입장 후 화면 이해"를 검증하는 예제로 잡는다.
- `wait_for_selector`는 Playwright `Page` 메서드이며, 현재 `session.page`를 기준으로 selector가 `visible` 상태가 될 때까지 step 실행을 블로킹한다.
- `wait_for_navigation`은 현재 ex03에서 `page.wait_for_load_state("domcontentloaded")`로 구현되어 있으며, 문서 로딩 완료를 기준으로 다음 단계 진행 여부를 판단한다.
- `wait_for_selector`는 AJAX/SPA 화면처럼 전체 navigation 없이 DOM 일부만 갱신되는 케이스에서 특히 유용하다.
