from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
import shlex
import time
from typing import Iterable
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

import yaml
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

MAX_ELEMENT_PREVIEW = 20
ROOT_DIR = Path(__file__).resolve().parents[2]
PLAYWRIGHT_DIR = ROOT_DIR / ".playwright"
DOM_TMP_FILE = PLAYWRIGHT_DIR / "_dom.tmp"
DOWNLOAD_EXTENSIONS = (".hwp", ".hwpx", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip")
LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "학습자 이름": ("학습자 이름", "학습자이름", "학습자", "학습자명", "성명", "이름"),
    "실습내용": ("실습내용", "실습 내용", "주제", "실습주제"),
    "제출 실습내용": ("제출 실습내용", "제출실습내용", "제출 내용", "제출내용"),
}


class CommandParseError(ValueError):
    """Raised when a CLI browser command cannot be parsed or validated."""


@dataclass(frozen=True, slots=True)
class BrowserCommand:
    name: str
    args: tuple[str, ...]
    raw: str


@dataclass(frozen=True, slots=True)
class BrowserSessionConfig:
    headed: bool = False
    slow_mo: int = 0
    timeout_ms: float = 5000.0


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    message: str


class BrowserSession:
    """Manage one Playwright Firefox session across multiple commands."""

    def __init__(self, config: BrowserSessionConfig) -> None:
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> "BrowserSession":
        self.open()
        return self

    @property
    def is_open(self) -> bool:
        return self._page is not None

    def open(self) -> None:
        if self.is_open:
            return

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.firefox.launch(
            headless=not self.config.headed,
            slow_mo=self.config.slow_mo,
        )
        self._context = self._browser.new_context()
        self._context.on("page", self._handle_new_page)
        self._page = self._context.new_page()
        self._handle_new_page(self._page)
        return None

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def page(self) -> Page:
        if self._page is not None and not self._page.is_closed():
            return self._page

        if self._context is not None:
            open_pages = [page for page in self._context.pages if not page.is_closed()]
            if open_pages:
                self._page = open_pages[-1]
                return self._page

        if self._page is None:
            raise RuntimeError("Browser session is not open. Open it first.")
        raise RuntimeError("No active page is available. Open a page first.")

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("Browser context is not open. Open it first.")
        return self._context

    def execute(self, command: BrowserCommand) -> tuple[CommandResult, bool]:
        return _execute_command(self, command)

    def click(self, selector: str) -> str | None:
        page = self.page
        existing_page_ids = {
            id(candidate)
            for candidate in self.context.pages
            if not candidate.is_closed()
        }
        page.locator(selector).first.click()

        popup = self._wait_for_new_page(existing_page_ids)
        if popup is None:
            return None

        self._page = popup
        try:
            popup.bring_to_front()
        except PlaywrightTimeoutError:
            pass

        return popup.url or "<new page>"

    def _prepare_page(self, page: Page) -> None:
        page.set_default_timeout(self.config.timeout_ms)

    def _handle_new_page(self, page: Page) -> None:
        self._prepare_page(page)
        self._page = page

    def _wait_for_new_page(self, existing_page_ids: set[int]) -> Page | None:
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            for candidate in self.context.pages:
                if candidate.is_closed() or id(candidate) in existing_page_ids:
                    continue

                self._prepare_page(candidate)
                try:
                    candidate.wait_for_load_state("domcontentloaded", timeout=self.config.timeout_ms)
                except (PlaywrightError, PlaywrightTimeoutError):
                    pass
                return candidate

            page = self._page
            if page is None or page.is_closed():
                time.sleep(0.05)
            else:
                page.wait_for_timeout(50)
        return None

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        finally:
            self._context = None
            self._page = None
            try:
                if self._browser is not None:
                    self._browser.close()
            finally:
                self._browser = None
                if self._playwright is not None:
                    self._playwright.stop()
                    self._playwright = None


def parse_command(raw: str) -> BrowserCommand:
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        raise CommandParseError(f"Could not parse command {raw!r}: {exc}") from exc

    if not parts:
        raise CommandParseError("Empty command strings are not allowed.")

    name = parts[0].lower()
    args = tuple(parts[1:])
    _validate_command(name, args)
    return BrowserCommand(name=name, args=args, raw=raw)


def run_commands(
    commands: Iterable[BrowserCommand],
    config: BrowserSessionConfig,
) -> list[CommandResult]:
    results: list[CommandResult] = []

    with BrowserSession(config) as session:
        for command in commands:
            result, should_stop = session.execute(command)
            results.append(result)
            if should_stop:
                break

    return results


def _validate_command(name: str, args: tuple[str, ...]) -> None:
    expected_args = {
        "goto": 1,
        "open": 1,
        "click": 1,
        "hover": 1,
        "clickable": 0,
        "clickables": 0,
        "elements": 1,
        "type": 2,
        "fill": 2,
        "clear": 1,
        "value": 1,
        "screenshot": 1,
        "save_yaml": -1,
        "download_links": -1,
        "dom": 0,
        "title": 0,
        "close": 0,
    }

    # wait는 1~2개 인자를 받으므로 별도 처리
    if name == "wait":
        if len(args) < 1 or len(args) > 2:
            raise CommandParseError("wait expects 1 or 2 arguments: wait <seconds> [max_seconds]")
        for i, arg in enumerate(args):
            try:
                val = float(arg)
            except ValueError as exc:
                raise CommandParseError("wait expects numeric values in seconds.") from exc
            if val < 0:
                raise CommandParseError("wait expects non-negative numbers.")
        if len(args) == 2 and float(args[0]) > float(args[1]):
            raise CommandParseError("wait: min must be <= max.")
        return

    if name == "save_yaml":
        if len(args) < 2:
            raise CommandParseError(
                "save_yaml expects at least 2 arguments: save_yaml <path> <label> [label...]"
            )
        return

    if name == "download_links":
        if len(args) < 1 or len(args) > 2:
            raise CommandParseError(
                "download_links expects 1 or 2 arguments: download_links <selector> [dir]"
            )
        return

    if name not in expected_args:
        supported = ", ".join(sorted(expected_args)) + ", wait"
        raise CommandParseError(f"Unsupported command {name!r}. Supported commands: {supported}")

    required = expected_args[name]
    if len(args) != required:
        raise CommandParseError(
            f"Command {name!r} expects {required} argument(s), got {len(args)}."
        )


def _execute_command(
    session: BrowserSession,
    command: BrowserCommand,
) -> tuple[CommandResult, bool]:
    name = command.name
    page = session.page

    if name in {"goto", "open"}:
        url = command.args[0]
        page.goto(url, wait_until="domcontentloaded")
        return CommandResult(command.raw, f"opened {url}"), False

    if name == "click":
        selector = command.args[0]
        popup_url = session.click(selector)
        if popup_url is None:
            return CommandResult(command.raw, f"clicked {selector}"), False
        return CommandResult(
            command.raw,
            f"clicked {selector} -> switched to new page {popup_url}",
        ), False

    if name == "hover":
        selector = command.args[0]
        page.locator(selector).first.hover()
        return CommandResult(command.raw, f"hovered {selector}"), False

    if name in {"clickable", "clickables"}:
        return CommandResult(command.raw, _describe_clickables(page)), False

    if name == "elements":
        selector = command.args[0]
        return CommandResult(command.raw, _describe_elements(page, selector)), False

    if name == "type":
        selector, text = command.args
        locator = page.locator(selector).first
        locator.click()
        locator.type(text)
        return CommandResult(command.raw, f"typed into {selector}"), False

    if name == "fill":
        selector, text = command.args
        locator = page.locator(selector).first
        locator.fill(text)
        return CommandResult(command.raw, f"filled {selector}"), False

    if name == "clear":
        selector = command.args[0]
        locator = page.locator(selector).first
        locator.fill("")
        return CommandResult(command.raw, f"cleared {selector}"), False

    if name == "value":
        selector = command.args[0]
        locator = page.locator(selector).first
        return CommandResult(command.raw, f"value: {locator.input_value()}"), False

    if name == "wait":
        if len(command.args) == 2:
            lo, hi = float(command.args[0]), float(command.args[1])
            seconds = random.uniform(lo, hi)
        else:
            seconds = float(command.args[0])
        page.wait_for_timeout(seconds * 1000)
        return CommandResult(command.raw, f"waited {seconds:.2f}s"), False

    if name == "screenshot":
        target = Path(command.args[0])
        target = _resolve_playwright_path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(target), full_page=True)
        return CommandResult(command.raw, f"saved screenshot to {target}"), False

    if name == "save_yaml":
        target = _resolve_playwright_path(Path(command.args[0]))
        labels = command.args[1:]
        target.parent.mkdir(parents=True, exist_ok=True)

        extracted, missing = _extract_labeled_fields(page, labels)
        target.write_text(
            yaml.safe_dump(extracted, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        message = f"saved YAML to {target}"
        if missing:
            message += f" (missing: {', '.join(missing)})"
        return CommandResult(command.raw, message), False

    if name == "download_links":
        selector = command.args[0]
        target_dir = Path(command.args[1]) if len(command.args) == 2 else Path("downloads")
        target_dir = _resolve_playwright_path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        locator = page.locator(selector)
        count = locator.count()
        if count == 0:
            return CommandResult(
                command.raw,
                f"downloaded 0 file(s) from selector {selector}",
            ), False

        saved_paths: list[Path] = []
        skipped: list[str] = []
        for index in range(count):
            link = page.locator(selector).nth(index)
            if not link.is_visible():
                continue

            href = (link.get_attribute("href") or "").strip()
            text = (link.text_content() or "").strip()
            label = text or href or f"link #{index + 1}"

            if href and _looks_like_download_href(href):
                try:
                    destination = _download_via_href(
                        session=session,
                        base_url=page.url,
                        href=href,
                        target_dir=target_dir,
                        label=label,
                        index=index,
                    )
                except OSError:
                    skipped.append(label)
                    continue
                saved_paths.append(destination)
                continue

            try:
                with page.expect_download(timeout=session.config.timeout_ms) as download_info:
                    link.click()
                download = download_info.value
            except PlaywrightTimeoutError:
                if href and not href.lower().startswith(("javascript:", "#", "#:")):
                    try:
                        destination = _download_via_href(
                            session=session,
                            base_url=page.url,
                            href=href,
                            target_dir=target_dir,
                            label=label,
                            index=index,
                        )
                    except OSError:
                        skipped.append(label)
                        continue
                    saved_paths.append(destination)
                    continue

                skipped.append(label)
                continue

            suggested_name = download.suggested_filename or f"download-{index + 1}"
            destination = _ensure_unique_path(target_dir / suggested_name)
            download.save_as(str(destination))
            saved_paths.append(destination)

        if not saved_paths:
            message = f"downloaded 0 file(s) from selector {selector}"
            if skipped:
                preview = ", ".join(skipped[:3])
                if len(skipped) > 3:
                    preview += ", ..."
                message += f" (matched but no download event: {preview})"
            return CommandResult(command.raw, message), False

        preview = ", ".join(path.name for path in saved_paths[:5])
        if len(saved_paths) > 5:
            preview += ", ..."

        message = f"downloaded {len(saved_paths)} file(s) to {target_dir}: {preview}"
        if skipped:
            message += f" (skipped {len(skipped)} non-download link(s))"
        return CommandResult(command.raw, message), False

    if name == "dom":
        content = page.content()
        PLAYWRIGHT_DIR.mkdir(parents=True, exist_ok=True)
        DOM_TMP_FILE.write_text(content, encoding="utf-8")
        return CommandResult(command.raw, f"saved DOM to {DOM_TMP_FILE} ({len(content)} chars)"), False

    if name == "title":
        return CommandResult(command.raw, f"title: {page.title()}"), False

    if name == "close":
        return CommandResult(command.raw, "closing browser session"), True

    raise CommandParseError(f"Unhandled command {name!r}.")


def _describe_elements(page: Page, selector: str) -> str:
    locator = page.locator(selector)
    count = locator.count()
    if count == 0:
        return f"matched 0 elements for selector: {selector}"

    items = locator.evaluate_all(
        """
        (elements, maxItems) => elements.slice(0, maxItems).map((element, index) => ({
            index,
            tag: element.tagName.toLowerCase(),
            id: element.id || "",
            name: element.getAttribute("name") || "",
            type: element.getAttribute("type") || "",
            value: "value" in element ? String(element.value || "") : "",
            placeholder: element.getAttribute("placeholder") || "",
            text: (element.textContent || "").replace(/\\s+/g, " ").trim().slice(0, 80)
        }))
        """,
        MAX_ELEMENT_PREVIEW,
    )

    lines = [f"matched {count} element(s) for selector: {selector}"]
    for item in items:
        parts = [f"{item['index']}. <{item['tag']}>"]
        if item["id"]:
            parts.append(f"id={item['id']}")
        if item["name"]:
            parts.append(f"name={item['name']}")
        if item["type"]:
            parts.append(f"type={item['type']}")
        if item["placeholder"]:
            parts.append(f"placeholder={item['placeholder']}")
        if item["value"]:
            parts.append(f"value={item['value']}")
        if item["text"]:
            parts.append(f"text={item['text']}")
        lines.append(" | ".join(parts))

    if count > MAX_ELEMENT_PREVIEW:
        lines.append(f"... showing first {MAX_ELEMENT_PREVIEW} of {count} matches")

    return "\n".join(lines)


def _describe_clickables(page: Page) -> str:
    selector = "a[href], button, input[type=button], input[type=submit], input[type=reset], [role=button], [onclick]"
    locator = page.locator(selector)
    count = locator.count()
    if count == 0:
        return "matched 0 clickable elements"

    items = locator.evaluate_all(
        """
        (elements, maxItems) => elements.slice(0, maxItems).map((element, index) => {
            const className = typeof element.className === "string"
                ? element.className.trim().replace(/\\s+/g, " ")
                : "";
            const text = (
                element.textContent ||
                element.getAttribute("value") ||
                element.getAttribute("aria-label") ||
                ""
            ).replace(/\\s+/g, " ").trim().slice(0, 80);

            return {
                index,
                tag: element.tagName.toLowerCase(),
                id: element.id || "",
                className,
                name: element.getAttribute("name") || "",
                type: element.getAttribute("type") || "",
                role: element.getAttribute("role") || "",
                href: element.getAttribute("href") || "",
                onclick: (element.getAttribute("onclick") || "").replace(/\\s+/g, " ").trim().slice(0, 120),
                text,
            };
        })
        """,
        MAX_ELEMENT_PREVIEW,
    )

    lines = [f"matched {count} clickable element(s)"]
    for item in items:
        parts = [f"{item['index']}. <{item['tag']}>"]
        if item["id"]:
            parts.append(f"id={item['id']}")
        if item["className"]:
            parts.append(f"class={item['className']}")
        if item["name"]:
            parts.append(f"name={item['name']}")
        if item["type"]:
            parts.append(f"type={item['type']}")
        if item["role"]:
            parts.append(f"role={item['role']}")
        if item["text"]:
            parts.append(f"text={item['text']}")
        if item["href"]:
            parts.append(f"href={item['href']}")
        if item["onclick"]:
            parts.append(f"onclick={item['onclick']}")

        hint = _build_selector_hint(item)
        if hint:
            parts.append(f"hint={hint}")

        lines.append(" | ".join(parts))

    if count > MAX_ELEMENT_PREVIEW:
        lines.append(f"... showing first {MAX_ELEMENT_PREVIEW} of {count} matches")

    return "\n".join(lines)


def _build_selector_hint(item: dict[str, str]) -> str | None:
    tag = item["tag"]
    element_id = item["id"]
    if element_id and " " not in element_id:
        return f"#{element_id}"

    name = item["name"]
    if tag == "input" and name:
        return f'input[name="{name}"]'

    href = item["href"]
    if tag == "a" and href:
        return f'a[href="{href}"]'

    class_name = item["className"]
    if class_name:
        first_class = class_name.split(" ")[0]
        if first_class and " " not in first_class:
            return f"{tag}.{first_class}"

    role = item["role"]
    if role:
        return f'[role="{role}"]'

    onclick = item["onclick"]
    if onclick:
        return f"{tag}[onclick]"

    return tag


def _resolve_playwright_path(target: Path) -> Path:
    if target.is_absolute():
        return target
    return PLAYWRIGHT_DIR / target


def _ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _extract_labeled_fields(page: Page, labels: tuple[str, ...]) -> tuple[dict[str, str], list[str]]:
    search_labels = [list(LABEL_ALIASES.get(label, (label,))) for label in labels]
    result = page.evaluate(
        """
        (payload) => {
            const labels = payload.labels;
            const searchLabels = payload.searchLabels;
            const normalize = (value) => (value || "")
                .replace(/\\u00a0/g, " ")
                .replace(/\\s+/g, " ")
                .trim();
            const compact = (value) => normalize(value).replace(/\\s+/g, "");
            const trimLabelSuffix = (value) => normalize(value).replace(/[\\s:：-]+$/, "");

            const valueOf = (element) => {
                if (!element) {
                    return "";
                }

                const tagName = (element.tagName || "").toUpperCase();
                if (["INPUT", "TEXTAREA", "SELECT"].includes(tagName)) {
                    return normalize(element.value || "");
                }

                const controlValues = Array.from(
                    element.querySelectorAll("textarea, input, select")
                )
                    .map((child) => normalize(child.value || ""))
                    .filter(Boolean);
                if (controlValues.length > 0) {
                    return controlValues.join("\\n");
                }

                return normalize(element.innerText || element.textContent || "");
            };

            const inlineValue = (text, label) => {
                const raw = normalize(text);
                if (!raw) {
                    return "";
                }

                const normalizedLabel = compact(label);
                const normalizedText = compact(raw);
                if (normalizedText === normalizedLabel || !normalizedText.startsWith(normalizedLabel)) {
                    return "";
                }

                const labelText = normalize(label);
                if (!raw.startsWith(labelText)) {
                    return "";
                }

                return normalize(raw.slice(labelText.length).replace(/^[:：-]\\s*/, ""));
            };

            const findValue = (variants) => {
                const targets = variants.map((label) => compact(label));

                for (const row of document.querySelectorAll("tr")) {
                    const cells = Array.from(row.children).filter((child) =>
                        ["TH", "TD"].includes((child.tagName || "").toUpperCase())
                    );
                    for (let index = 0; index < cells.length; index += 1) {
                        const cellText = valueOf(cells[index]);
                        if (targets.includes(compact(trimLabelSuffix(cellText)))) {
                            const rest = cells.slice(index + 1).map(valueOf).filter(Boolean);
                            if (rest.length > 0) {
                                return rest.join("\\n");
                            }
                        }

                        for (const label of variants) {
                            const inline = inlineValue(cellText, label);
                            if (inline) {
                                return inline;
                            }
                        }
                    }
                }

                for (const dt of document.querySelectorAll("dt")) {
                    const dtText = valueOf(dt);
                    if (!targets.includes(compact(trimLabelSuffix(dtText)))) {
                        continue;
                    }

                    const dd = dt.nextElementSibling;
                    if (dd && (dd.tagName || "").toUpperCase() === "DD") {
                        const ddText = valueOf(dd);
                        if (ddText) {
                            return ddText;
                        }
                    }
                }

                const candidates = document.querySelectorAll(
                    "label, th, td, dt, dd, span, div, p, strong, b, li"
                );
                for (const element of candidates) {
                    const text = valueOf(element);
                    if (!text) {
                        continue;
                    }

                    if (targets.includes(compact(trimLabelSuffix(text)))) {
                        const next = element.nextElementSibling;
                        if (next) {
                            const nextText = valueOf(next);
                            if (nextText) {
                                return nextText;
                            }
                        }

                        const parent = element.parentElement;
                        if (parent) {
                            const siblings = Array.from(parent.children);
                            const index = siblings.indexOf(element);
                            if (index >= 0) {
                                const rest = siblings.slice(index + 1).map(valueOf).filter(Boolean);
                                if (rest.length > 0) {
                                    return rest.join("\\n");
                                }
                            }
                        }
                    }

                    for (const label of variants) {
                        const inline = inlineValue(text, label);
                        if (inline) {
                            return inline;
                        }
                    }
                }

                return "";
            };

            const values = {};
            const missing = [];
            for (let index = 0; index < labels.length; index += 1) {
                const label = labels[index];
                const value = findValue(searchLabels[index]);
                values[label] = value;
                if (!value) {
                    missing.push(label);
                }
            }

            return { values, missing };
        }
        """,
        {"labels": list(labels), "searchLabels": search_labels},
    )

    values = {key: str(value) for key, value in result["values"].items()}
    missing = [label for label in labels if label in set(result["missing"])]
    return values, missing


def _looks_like_download_href(href: str) -> bool:
    lower_href = href.lower()
    if lower_href.startswith(("javascript:", "#", "#:")):
        return False
    if any(lower_href.endswith(ext) for ext in DOWNLOAD_EXTENSIONS):
        return True
    return "filedown" in lower_href or "download" in lower_href


def _download_via_href(
    session: BrowserSession,
    base_url: str,
    href: str,
    target_dir: Path,
    label: str,
    index: int,
) -> Path:
    absolute_url = urljoin(base_url, href)
    cookies = session.context.cookies([absolute_url])
    cookie_header = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in cookies)

    headers = {
        "User-Agent": session.page.evaluate("() => navigator.userAgent"),
        "Referer": base_url,
    }
    if cookie_header:
        headers["Cookie"] = cookie_header

    request = Request(absolute_url, headers=headers)
    timeout_seconds = max(session.config.timeout_ms / 1000.0, 1.0)
    with urlopen(request, timeout=timeout_seconds) as response:
        filename = _filename_from_content_disposition(response.headers.get("Content-Disposition"))
        if not filename:
            resolved_url = getattr(response, "url", absolute_url)
            filename = _filename_from_url(resolved_url)
        if not filename:
            filename = _sanitize_filename(label) or f"download-{index + 1}"

        destination = _ensure_unique_path(target_dir / filename)
        destination.write_bytes(response.read())
        return destination


def _filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None

    parts = [part.strip() for part in value.split(";")]
    for part in parts:
        if part.lower().startswith("filename*="):
            encoded = part.split("=", 1)[1].strip().strip('"')
            if "''" in encoded:
                encoded = encoded.split("''", 1)[1]
            return unquote(encoded)

    for part in parts:
        if part.lower().startswith("filename="):
            return part.split("=", 1)[1].strip().strip('"')

    return None


def _filename_from_url(url: str) -> str | None:
    path = urlparse(url).path
    filename = Path(unquote(path)).name
    return filename or None


def _sanitize_filename(value: str) -> str:
    sanitized = "".join(char if char not in '<>:"/\\\\|?*' else "_" for char in value).strip()
    return sanitized[:120]
