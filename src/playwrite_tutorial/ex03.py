"""ex03 – REPL + 스마트 태스크 러너.

ex02의 매크로를 업그레이드하여 각 단계의 성공/실패를 확인하고,
페이지 로딩을 셀렉터 기반으로 대기하며, 실패 시 정책(stop/skip/retry)을 적용한다.

system.yaml 예시:
  tasks:
    login_example:
      description: "로그인 예시"
      steps:
        - action: "goto https://example.com"
          wait_for: "input[name=id]"        # 셀렉터가 나타날 때까지 대기
        - action: "fill input[name=id] myid"
        - action: "click button[type=submit]"
          wait_for_navigation: true          # 페이지 전환 완료 대기
          on_fail: stop                      # stop / skip / retry

사용법:
  uv run ex03_tasks
  uv run ex03_tasks --system my_tasks.yaml
"""
from __future__ import annotations

import queue
import shlex
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from .browser import (
    BrowserSession,
    BrowserSessionConfig,
    CommandParseError,
    CommandResult,
    parse_command,
)
from .macros import get_system_file, load_macros, set_system_file

PROMPT = "browser> "
HELP_TEXT = """\
브라우저 명령 예시:
  goto https://example.com
  dom
  clickables
  elements "input"
  title
  click "text=More information"
  hover "a.has-submenu:has-text('K크래딧')"
  type "input[name=q]" "playwright python"
  fill "input[name=adminid]" "teacher01"
  clear "input[name=adminid]"
  value "input[name=adminid]"
  save_yaml practice.yaml "학습자 이름" "실습내용" "제출 실습내용"
  download_links "a[href*='download'], a:has-text('다운로드')" downloads
  wait 1.5
  wait 1 3            (1~3초 사이 랜덤 대기)
  screenshot ex03.png
  close

태스크 명령:
  tasks                     태스크 목록 보기
  task <name|number>        태스크 실행

매크로 명령 (ex02 호환):
  macros                    매크로 목록 보기
  macro <name>              매크로 실행

로컬 명령:
  help / status / open_browser / close_browser / exit / quit
"""


# ---------------------------------------------------------------------------
# Task data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TaskStep:
    action: str
    wait_for: str | None = None
    wait_for_navigation: bool = False
    on_fail: str = "stop"  # stop / skip / retry


@dataclass(frozen=True, slots=True)
class TaskDef:
    name: str
    description: str
    steps: list[TaskStep] = field(default_factory=list)


def _load_tasks() -> dict[str, TaskDef]:
    """system.yaml의 tasks 섹션을 파싱한다."""
    import yaml

    path = get_system_file()
    if not path.exists():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}

    if not isinstance(data, dict) or not isinstance(data.get("tasks"), dict):
        return {}

    result: dict[str, TaskDef] = {}
    for name, body in data["tasks"].items():
        if not isinstance(body, dict):
            continue
        raw_steps = body.get("steps", [])
        if not isinstance(raw_steps, list):
            continue

        steps: list[TaskStep] = []
        for s in raw_steps:
            if isinstance(s, str):
                steps.append(TaskStep(action=s))
            elif isinstance(s, dict) and "action" in s:
                on_fail = str(s.get("on_fail", "stop")).lower()
                if on_fail not in {"stop", "skip", "retry"}:
                    on_fail = "stop"
                steps.append(TaskStep(
                    action=s["action"],
                    wait_for=s.get("wait_for"),
                    wait_for_navigation=bool(s.get("wait_for_navigation", False)),
                    on_fail=on_fail,
                ))

        result[str(name)] = TaskDef(
            name=str(name),
            description=str(body.get("description", "")),
            steps=steps,
        )
    return result


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------

def _run_task(session: BrowserSession, task: TaskDef) -> bool:
    """태스크의 모든 step을 실행한다. True를 반환하면 REPL 종료."""
    print(f"[task] {task.name} -> {len(task.steps)} step(s)")

    for index, step in enumerate(task.steps, start=1):
        label = f"[task {task.name}] {index}/{len(task.steps)}"
        print(f"{label} {step.action}")

        success = _execute_step(session, step, label)

        if success:
            print(f"{label} [OK]")
        else:
            if step.on_fail == "skip":
                print(f"{label} [SKIP] on_fail=skip -> 다음 단계로 넘어갑니다")
                continue
            elif step.on_fail == "retry":
                print(f"{label} [RETRY] 한 번 더 시도합니다...")
                success = _execute_step(session, step, label)
                if success:
                    print(f"{label} [OK] 재시도 성공")
                else:
                    print(f"{label} [FAIL] 재시도도 실패 -> 태스크 중단")
                    return False
            else:  # stop
                print(f"{label} [FAIL] on_fail=stop -> 태스크 중단")
                return False

    print(f"[task] {task.name} -> completed")
    return False


def _execute_step(session: BrowserSession, step: TaskStep, label: str) -> bool:
    """단일 step을 실행하고 성공 여부를 반환한다."""
    if not session.is_open:
        print(f"{label} [error] Browser is closed.")
        return False

    # 1) 액션 실행
    try:
        command = parse_command(step.action)
    except CommandParseError as exc:
        print(f"{label} [error] parse: {exc}")
        return False

    try:
        result, _ = session.execute(command)
    except PlaywrightError as exc:
        print(f"{label} [error] {_format_playwright_error(exc)}")
        return False

    _print_result(_display_command(result.command), result.message)

    # 2) wait_for_navigation: 페이지 전환 완료 대기
    if step.wait_for_navigation:
        try:
            session.page.wait_for_load_state("domcontentloaded")
            print(f"{label} [nav] page loaded")
        except PlaywrightError as exc:
            print(f"{label} [error] navigation: {_format_playwright_error(exc)}")
            return False

    # 3) wait_for: 셀렉터가 나타날 때까지 대기
    if step.wait_for:
        try:
            session.page.wait_for_selector(step.wait_for, state="visible")
            print(f"{label} [wait] {step.wait_for} -> visible")
        except PlaywrightError as exc:
            print(f"{label} [error] wait_for {step.wait_for}: {_format_playwright_error(exc)}")
            return False

    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> Path | None:
    i = 0
    while i < len(argv):
        if argv[i] == "--system" and i + 1 < len(argv):
            return Path(argv[i + 1])
        i += 1
    return None


def main() -> int:
    system_path = _parse_args(sys.argv[1:])
    if system_path is not None:
        set_system_file(system_path)

    config = BrowserSessionConfig(
        headed=True,
        slow_mo=0,
        timeout_ms=5000.0,
    )

    command_queue: queue.Queue[str | None] = queue.Queue()
    stop_event = threading.Event()
    ready_event = threading.Event()
    ready_event.set()
    input_thread = threading.Thread(
        target=_read_commands_forever,
        args=(command_queue, stop_event, ready_event),
        daemon=True,
    )

    print("Firefox interactive REPL + Tasks (ex03) started.")
    print("브라우저는 시작할 때 자동으로 열립니다.")
    print(f"시스템 파일: {get_system_file()}")
    print("`help`로 명령 예시를 보고, `exit` 또는 `quit`로 종료할 수 있습니다.")

    session = BrowserSession(config)
    try:
        session.open()
        print("[ok] browser opened")
        input_thread.start()

        while True:
            try:
                raw_command = command_queue.get(timeout=0.1)
            except queue.Empty:
                if stop_event.is_set():
                    break
                continue

            if raw_command is None:
                break

            command_text = raw_command.strip()
            if not command_text:
                ready_event.set()
                continue

            should_exit = _execute_repl_command(session, command_text, macro_stack=())
            ready_event.set()
            if should_exit:
                break
    except PlaywrightError as exc:
        print(_format_playwright_error(exc), file=sys.stderr)
        return 1
    finally:
        session.close()
        stop_event.set()

    return 0


def _read_commands_forever(
    command_queue: queue.Queue[str | None],
    stop_event: threading.Event,
    ready_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        ready_event.wait()
        ready_event.clear()
        try:
            command = input(PROMPT)
        except EOFError:
            command_queue.put(None)
            return
        except KeyboardInterrupt:
            command_queue.put("exit")
            return
        command_queue.put(command)


def _format_playwright_error(exc: PlaywrightError) -> str:
    message = str(exc)
    if "Executable doesn't exist" in message or "playwright install" in message:
        return f"{message}\nHint: run `uv run playwright install firefox` first."
    return message


def _execute_repl_command(
    session: BrowserSession,
    command_text: str,
    macro_stack: tuple[str, ...],
) -> bool:
    lowered = command_text.lower()

    if lowered in {"exit", "quit"}:
        print("프로그램을 종료합니다.")
        return True
    if lowered == "help":
        print(HELP_TEXT)
        return False
    if lowered == "tasks":
        _print_tasks()
        return False
    if lowered == "macros":
        _print_macros()
        return False
    if lowered == "status":
        state = "open" if session.is_open else "closed"
        print(f"[ok] browser status -> {state}")
        return False
    if lowered == "open_browser":
        try:
            if session.is_open:
                print("[ok] open_browser -> browser already open")
            else:
                session.open()
                print("[ok] open_browser -> browser opened")
        except PlaywrightError as exc:
            print(f"[error] {_format_playwright_error(exc)}", file=sys.stderr)
        return False
    if lowered in {"close", "close_browser"}:
        if session.is_open:
            session.close()
            print("[ok] close_browser -> browser closed")
        else:
            print("[ok] close_browser -> browser already closed")
        return False

    # task <name|number>
    task_ref = _parse_named_command(command_text, "task")
    if task_ref is not None:
        tasks = _load_tasks()
        task = _resolve_task(tasks, task_ref)
        if task is None:
            print(f"[error] task not found: {task_ref}")
        else:
            return _run_task(session, task)
        return False

    # macro <name> (ex02 호환)
    macro_name = _parse_named_command(command_text, "macro")
    if macro_name is not None:
        return _run_macro(session, macro_name, macro_stack)

    if not session.is_open:
        print("[error] Browser is closed. Run `open_browser` first.")
        return False

    try:
        command = parse_command(command_text)
    except CommandParseError as exc:
        print(f"[error] {exc}")
        return False

    try:
        result, _ = session.execute(command)
    except PlaywrightError as exc:
        print(f"[error] {_format_playwright_error(exc)}", file=sys.stderr)
        return False

    _print_result(_display_command(result.command), result.message)
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_named_command(command_text: str, keyword: str) -> str | None:
    try:
        parts = shlex.split(command_text)
    except ValueError:
        return None
    if len(parts) == 2 and parts[0].lower() == keyword:
        return parts[1]
    return None


def _print_tasks() -> None:
    tasks = _load_tasks()
    if not tasks:
        print(f"[ok] tasks -> no tasks found in {get_system_file()}")
        return
    print("[ok] tasks")
    for index, (name, task) in enumerate(tasks.items(), start=1):
        desc = f" – {task.description}" if task.description else ""
        print(f"  {index}. {name} ({len(task.steps)} steps){desc}")


def _resolve_task(tasks: dict[str, TaskDef], task_ref: str) -> TaskDef | None:
    if task_ref in tasks:
        return tasks[task_ref]

    if task_ref.isdigit():
        index = int(task_ref)
        if index < 1:
            return None

        ordered_tasks = list(tasks.values())
        if index <= len(ordered_tasks):
            return ordered_tasks[index - 1]

    return None


def _print_macros() -> None:
    from .macros import load_macros
    macros = load_macros()
    if not macros:
        print(f"[ok] macros -> no macros found in {get_system_file()}")
        return
    print("[ok] macros")
    for name in sorted(macros):
        print(f"  - {name} ({len(macros[name])} commands)")


def _run_macro(
    session: BrowserSession,
    name: str,
    macro_stack: tuple[str, ...],
) -> bool:
    if name in macro_stack:
        chain = " -> ".join((*macro_stack, name))
        print(f"[error] macro recursion detected: {chain}")
        return False

    from .macros import load_macro
    commands = load_macro(name)
    if commands is None:
        print(f"[error] macro not found: {name}")
        return False

    print(f"[ok] macro {name} -> running {len(commands)} command(s)")
    next_stack = (*macro_stack, name)
    for index, raw_command in enumerate(commands, start=1):
        command_text = raw_command.strip()
        if not command_text:
            continue
        print(f"[macro {name}] {index}/{len(commands)}")
        should_exit = _execute_repl_command(session, command_text, macro_stack=next_stack)
        if should_exit:
            return True
    print(f"[ok] macro {name} -> completed")
    return False


def _print_result(command: str, message: str) -> None:
    if "\n" in message:
        print(f"[ok] {command}")
        print(message)
        return
    print(f"[ok] {command} -> {message}")


def _display_command(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        return command
    if len(parts) >= 3 and parts[0] in {"type", "fill"}:
        return f"{parts[0]} {parts[1]} <hidden>"
    return command


if __name__ == "__main__":
    raise SystemExit(main())
