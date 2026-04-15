# _forAI Guide

## 한 줄 요약

이 디렉터리는 `playwrite_tutorial` 작업을 이어받을 때 필요한 AI 작업 문맥을 정리해 두는 곳이다.

## 읽는 순서

1. `README.md`
2. `inventory.md`
3. `memo.md`
4. `dev_log.md`
5. `plan.md`

## 문서 역할

- `inventory.md`: 저장소에 실제로 있는 구조, 엔트리포인트, 실행 및 검증 명령을 기록한다.
- `plan.md`: 앞으로 진행할 개발 계획과 우선순위만 기록한다.
- `memo.md`: 런타임 규칙, 기본값, 레거시 fallback, 디버깅 교훈 같은 참고 메모를 모은다.
- `dev_log.md`: 날짜별 작업 이력과 `_forAI` 정리 내역을 남긴다.

## 현재 스냅샷

- 저장소 경로: `/Volumes/data/work/aiwork/playwrite_tutorial`
- 현재 버전: `0.1.0`
- 메인 엔트리포인트: `uv run ex01_repl`, `uv run ex02_macro`, `uv run ex03_tasks`
- 보조 엔트리포인트: `uv run python main.py`, `uv run python -m playwrite_tutorial`

## 유지 규칙

- 저장소 구조나 실행 명령이 바뀌면 `inventory.md`를 먼저 갱신한다.
- 계획이 아닌 구현 세부나 운영 규칙은 `plan.md`가 아니라 `memo.md`에 둔다.
- 작업 이력은 날짜를 붙여 `dev_log.md`에만 남긴다.
- 새 세션에서는 `inventory.md`와 `memo.md`를 먼저 읽고, 실제 남은 작업은 `plan.md`에서 확인한다.
