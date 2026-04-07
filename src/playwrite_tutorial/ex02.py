"""ex02 – REPL + 매크로 예제.

ex01의 REPL 기능에 YAML 기반 매크로 시스템을 추가한다.
system.yaml 파일에서 매크로를 정의하고, REPL에서 `macro <name>` 으로 실행한다.

사용법:
  uv run ex02_macro                           # .playwright/system.yaml 사용
  uv run ex02_macro --system my.yaml          # 지정한 파일 사용
"""
from __future__ import annotations

import queue
import shlex
import sys
import threading
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from .browser import BrowserSession, BrowserSessionConfig, CommandParseError, parse_command
from .macros import get_system_file, load_macro, load_macros, set_system_file

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
  screenshot ex02.png
  close

매크로 명령:
  macros                    매크로 목록 보기
  macro <name>              매크로 실행

로컬 명령:
  help
  status
  open_browser
  close_browser
  exit / quit
"""


def _parse_args(argv: list[str]) -> Path | None:
    """--system <path> 인자만 처리한다."""
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

    print("Firefox interactive REPL + Macro (ex02) started.")
    print("브라우저는 시작할 때 자동으로 열립니다.")
    print("브라우저를 닫았다면 `open_browser`로 다시 열 수 있습니다.")
    print(f"매크로 정의: {get_system_file()}")
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

    macro_name = _parse_macro_command(command_text)
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


def _print_macros() -> None:
    macros = load_macros()
    if not macros:
        print(f"[ok] macros -> no macros found in {get_system_file()}")
        return

    print("[ok] macros")
    for name in sorted(macros):
        print(f"  - {name} ({len(macros[name])} commands)")


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


def _parse_macro_command(command_text: str) -> str | None:
    try:
        parts = shlex.split(command_text)
    except ValueError:
        return None

    if len(parts) == 2 and parts[0].lower() == "macro":
        return parts[1]
    return None


def _run_macro(
    session: BrowserSession,
    name: str,
    macro_stack: tuple[str, ...],
) -> bool:
    if name in macro_stack:
        chain = " -> ".join((*macro_stack, name))
        print(f"[error] macro recursion detected: {chain}")
        return False

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


if __name__ == "__main__":
    raise SystemExit(main())
