"""ex01 순수 REPL 예제.

브라우저를 열고 명령을 한 줄씩 입력하면서 Playwright 기본 동작을 익힌다.
매크로 기능 없이 단순 REPL만 제공한다.
"""
from __future__ import annotations

import queue
import shlex
import sys
import threading

from playwright.sync_api import Error as PlaywrightError

from .browser import BrowserSession, BrowserSessionConfig, CommandParseError, parse_command

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
  screenshot ex01.png
  close

로컬 명령:
  help
  status
  open_browser
  close_browser
  exit / quit
"""


def main() -> int:
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

    print("Firefox interactive REPL (ex01) started.")
    print("브라우저는 시작할 때 자동으로 열립니다.")
    print("브라우저를 닫았다면 `open_browser`로 다시 열 수 있습니다.")
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

            should_exit = _execute_repl_command(session, command_text)
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


def _execute_repl_command(session: BrowserSession, command_text: str) -> bool:
    lowered = command_text.lower()

    if lowered in {"exit", "quit"}:
        print("프로그램을 종료합니다.")
        return True
    if lowered == "help":
        print(HELP_TEXT)
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
