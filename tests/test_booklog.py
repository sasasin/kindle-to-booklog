from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kindle_to_booklog.booklog import add_books_to_booklog


class FakeLocator:
    def __init__(self) -> None:
        self.clicked = False
        self.filled_with: str | None = None
        self.selected_value: str | None = None

    def click(self) -> None:
        self.clicked = True

    def fill(self, value: str) -> None:
        self.filled_with = value

    def select_option(self, value: str) -> None:
        self.selected_value = value


class FakePage:
    def __init__(self, *, requires_login: bool, input_url: str) -> None:
        self.requires_login = requires_login
        self.input_url = input_url
        self.url = "about:blank"
        self.goto_calls: list[str] = []
        self.waited_urls: list[tuple[str, int | None]] = []
        self.role_locators: dict[tuple[str, str], FakeLocator] = {}
        self.label_locators: dict[str, FakeLocator] = {}

    def goto(self, url: str) -> None:
        self.goto_calls.append(url)
        if self.requires_login and len(self.goto_calls) == 1:
            self.url = "https://booklog.jp/login"
            return
        self.url = url

    def wait_for_url(self, url: str, timeout: int | None = None) -> None:
        self.waited_urls.append((url, timeout))
        self.url = url

    def get_by_role(self, role: str, *, name: str) -> FakeLocator:
        key = (role, name)
        if key not in self.role_locators:
            self.role_locators[key] = FakeLocator()
        return self.role_locators[key]

    def get_by_label(self, name: str) -> FakeLocator:
        if name not in self.label_locators:
            self.label_locators[name] = FakeLocator()
        return self.label_locators[name]


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.storage_state_paths: list[str] = []
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def storage_state(self, *, path: str) -> None:
        self.storage_state_paths.append(path)

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, context: FakeContext) -> None:
        self.context = context
        self.new_context_calls: list[dict[str, object]] = []
        self.closed = False

    def new_context(self, **kwargs):
        self.new_context_calls.append(kwargs)
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser
        self.launch_calls: list[dict[str, object]] = []

    def launch(self, **kwargs):
        self.launch_calls.append(kwargs)
        return self.browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium


class FakePlaywrightManager:
    def __init__(self, playwright: FakePlaywright) -> None:
        self.playwright = playwright

    def __enter__(self) -> FakePlaywright:
        return self.playwright

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class BooklogTests(unittest.TestCase):
    def test_add_books_uses_existing_session_without_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_file = Path(tmp_dir) / "session.json"
            session_file.write_text("{}", encoding="utf-8")

            page = FakePage(requires_login=False, input_url="https://booklog.jp/input")
            context = FakeContext(page)
            browser = FakeBrowser(context)
            chromium = FakeChromium(browser)

            add_books_to_booklog(
                ["B000000001", "B000000002"],
                playwright_factory=lambda: FakePlaywrightManager(
                    FakePlaywright(chromium)
                ),
                session_file=session_file,
                browser_channel="msedge",
            )

            self.assertEqual(
                chromium.launch_calls, [{"headless": False, "channel": "msedge"}]
            )
            self.assertEqual(
                browser.new_context_calls,
                [
                    {
                        "locale": "ja-JP",
                        "viewport": {"width": 1280, "height": 800},
                        "storage_state": str(session_file),
                    }
                ],
            )
            textbox = page.get_by_role("textbox", name="ISBN/ASINコード")
            self.assertTrue(textbox.clicked)
            self.assertEqual(textbox.filled_with, "B000000001\nB000000002")
            self.assertEqual(page.get_by_label("読書状況").selected_value, "4")
            self.assertEqual(context.storage_state_paths, [])
            self.assertTrue(context.closed)
            self.assertTrue(browser.closed)

    def test_add_books_saves_session_after_manual_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_file = Path(tmp_dir) / "session.json"

            page = FakePage(requires_login=True, input_url="https://booklog.jp/input")
            context = FakeContext(page)
            browser = FakeBrowser(context)
            chromium = FakeChromium(browser)

            add_books_to_booklog(
                ["B000000009"],
                playwright_factory=lambda: FakePlaywrightManager(
                    FakePlaywright(chromium)
                ),
                session_file=session_file,
            )

            self.assertEqual(
                page.goto_calls,
                ["https://booklog.jp/input", "https://booklog.jp/input"],
            )
            self.assertEqual(
                page.waited_urls,
                [
                    ("https://booklog.jp/input", 300_000),
                    ("https://booklog.jp/input", None),
                ],
            )
            self.assertEqual(context.storage_state_paths, [str(session_file)])


if __name__ == "__main__":
    unittest.main()
