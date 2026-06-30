"""Browser extension: navigate and interact with web pages."""

import asyncio
import inspect
import threading
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from inloop import contrib

_PROFILE_DIR = Path(__file__).resolve().parents[1] / "var"
_DEFAULT_TIMEOUT_MS = 15_000
_CHANNEL = "chrome"

_page = None
_playwright = None
_start_lock = None

# Persistent event loop: Playwright's browser session lives here across all calls.
_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


async def _init_lock():
    global _start_lock
    _start_lock = asyncio.Lock()


asyncio.run_coroutine_threadsafe(_init_lock(), _loop).result()


async def _get_page():
    global _page, _playwright
    async with _start_lock:
        if _page is not None:
            return _page
        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        _playwright = await async_playwright().start()
        context = await _playwright.chromium.launch_persistent_context(
            user_data_dir=str(_PROFILE_DIR), headless=False, viewport=None,
            channel=_CHANNEL, ignore_default_args=["--no-sandbox"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(_DEFAULT_TIMEOUT_MS)
        _page = page
        return _page


def _run(action):
    async def coro():
        try:
            page = await _get_page()
            result = action(page)
            return await result if inspect.isawaitable(result) else result
        except PlaywrightError as exc:
            raise RuntimeError(str(exc).strip().splitlines()[0]) from None
    return asyncio.run_coroutine_threadsafe(coro(), _loop).result()


@contrib.tool(
    name="navigate",
    description=(
        "Navigate the browser to a URL and wait for DOM content to load. "
        "Prefixes https:// if no protocol is given. "
        "Returns the final URL and page title."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to open."},
        },
        "required": ["url"],
    },
)
def navigate(args: dict[str, object]) -> str:
    url = str(args["url"])
    if not url.strip():
        raise RuntimeError("url must not be empty")
    if "://" not in url:
        url = "https://" + url
    async def go(page):
        await page.goto(url, wait_until="domcontentloaded")
        return f"loaded {page.url} — {await page.title()!r}"
    return _run(go)


@contrib.tool(
    name="snapshot",
    description=(
        "Return an accessibility-tree snapshot of the current page as YAML. "
        "Use to understand page structure and locate interactive elements before acting."
    ),
    parameters={"type": "object", "properties": {}},
)
def snapshot(args: dict[str, object]) -> str:
    return _run(lambda page: page.locator("body").aria_snapshot())


@contrib.tool(
    name="click",
    description="Click the first element matching a Playwright or CSS selector.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "Playwright or CSS selector for the element."},
        },
        "required": ["selector"],
    },
)
def click(args: dict[str, object]) -> None:
    selector = str(args["selector"])
    _run(lambda page: page.locator(selector).first.click())


@contrib.tool(
    name="fill",
    description="Fill an input, textarea, or contenteditable element with text.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "Playwright or CSS selector for the input."},
            "text": {"type": "string", "description": "The text to enter."},
        },
        "required": ["selector", "text"],
    },
)
def fill(args: dict[str, object]) -> None:
    selector = str(args["selector"])
    text = str(args["text"])
    _run(lambda page: page.locator(selector).first.fill(text))


@contrib.tool(
    name="press",
    description="Simulate pressing a key or chord (e.g. 'Enter', 'Control+a') on an element.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "Playwright or CSS selector for the element."},
            "key": {"type": "string", "description": "Key name or chord, e.g. 'Enter', 'Escape', 'Control+a'."},
        },
        "required": ["selector", "key"],
    },
)
def press(args: dict[str, object]) -> None:
    selector = str(args["selector"])
    key = str(args["key"])
    _run(lambda page: page.locator(selector).first.press(key))


@contrib.tool(
    name="get_text",
    description="Return the visible inner text of the first element matching the selector.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "Playwright or CSS selector for the element."},
        },
        "required": ["selector"],
    },
)
def get_text(args: dict[str, object]) -> str:
    selector = str(args["selector"])
    return _run(lambda page: page.locator(selector).first.inner_text())


@contrib.tool(
    name="current_url",
    description="Return the URL of the page currently open in the browser.",
    parameters={"type": "object", "properties": {}},
)
def current_url(args: dict[str, object]) -> str:
    return _run(lambda page: page.url)


@contrib.tool(
    name="wait_for",
    description=(
        "Wait until the first element matching the selector appears in the DOM. "
        "Raises an error if it does not appear within the timeout."
    ),
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "Playwright or CSS selector to wait for."},
            "timeout_ms": {"type": "integer", "description": "Maximum wait time in milliseconds (default 15000)."},
        },
        "required": ["selector"],
    },
)
def wait_for(args: dict[str, object]) -> None:
    selector = str(args["selector"])
    timeout_ms = int(args.get("timeout_ms", _DEFAULT_TIMEOUT_MS))
    _run(lambda page: page.locator(selector).first.wait_for(timeout=timeout_ms))


EXTENSION = contrib.Extension(
    name="browser",
    tools=[navigate, snapshot, click, fill, press, get_text, current_url, wait_for],
)
