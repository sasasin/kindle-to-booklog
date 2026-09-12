from __future__ import annotations

import sqlite3
import tempfile
import unittest
from typing import Any
from pathlib import Path

from kindle_to_booklog.kindle import (
    get_asin_list_from_kindle_windows_app_xml,
    load_asins_from_sqlite_path,
    load_asins_from_xml_path,
    parse_purchase_date,
)
from kindle_to_booklog.kindle import get_asin_list_from_kindle_web

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakeWebResponse:
    def __init__(self, payload: Any, *, ok: bool = True, status: int = 200) -> None:
        self.payload = payload
        self.ok = ok
        self.status = status

    def json(self) -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeWebRequest:
    def __init__(self, responses: dict[str, FakeWebResponse]) -> None:
        self.responses = responses
        self.get_calls: list[str] = []

    def get(self, url: str) -> FakeWebResponse:
        self.get_calls.append(url)
        response = self.responses.get(url)
        if response is None:
            raise AssertionError(f"unexpected request: {url}")
        return response


class FakeWebPage:
    def __init__(self, *, url: str) -> None:
        self.url = url
        self.goto_calls: list[str] = []
        self.waited_urls: list[tuple[Any, int | None]] = []

    def goto(self, url: str) -> None:
        self.goto_calls.append(url)

    def wait_for_url(self, url: Any, *, timeout: int | None = None) -> None:
        self.waited_urls.append((url, timeout))
        self.url = "https://read.amazon.co.jp/kindle-library"


class FakeWebContext:
    def __init__(self, page: FakeWebPage, request: FakeWebRequest) -> None:
        self.page = page
        self.request = request
        self.new_context_calls: list[dict[str, Any]] = []
        self.storage_state_paths: list[str] = []
        self.closed = False

    def new_page(self) -> FakeWebPage:
        return self.page

    def storage_state(self, *, path: str) -> None:
        self.storage_state_paths.append(path)

    def close(self) -> None:
        self.closed = True


class FakeWebBrowser:
    def __init__(self, context: FakeWebContext) -> None:
        self.context = context
        self.new_context_calls: list[dict[str, Any]] = []
        self.closed = False

    def new_context(self, **kwargs: Any) -> FakeWebContext:
        self.new_context_calls.append(kwargs)
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeWebChromium:
    def __init__(self, browser: FakeWebBrowser) -> None:
        self.browser = browser
        self.launch_calls: list[dict[str, Any]] = []

    def launch(self, **kwargs: Any) -> FakeWebBrowser:
        self.launch_calls.append(kwargs)
        return self.browser


class FakeWebPlaywright:
    def __init__(self, chromium: FakeWebChromium) -> None:
        self.chromium = chromium


class FakeWebPlaywrightManager:
    def __init__(self, playwright: FakeWebPlaywright) -> None:
        self.playwright = playwright

    def __enter__(self) -> FakeWebPlaywright:
        return self.playwright

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


def web_item(
    asin: str, *, resource_type: str = "EBOOK", origin_type: str = "PURCHASE"
) -> dict[str, str]:
    return {"asin": asin, "resourceType": resource_type, "originType": origin_type}


def web_payload(
    items: list[dict[str, str]], *, token: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"itemsList": items}
    if token is not None:
        payload["paginationToken"] = token
    return payload


class KindleTests(unittest.TestCase):
    def test_parse_purchase_date_supports_z_suffix(self) -> None:
        parsed = parse_purchase_date("2024-01-02T03:04:05Z")
        self.assertEqual(parsed.isoformat(), "2024-01-02T03:04:05+00:00")

    def test_parse_purchase_date_supports_windows_app_offset(self) -> None:
        parsed = parse_purchase_date("2026-06-18T07:29:50+0000")
        self.assertEqual(parsed.isoformat(), "2026-06-18T07:29:50+00:00")

    def test_load_asins_from_xml_path_filters_and_orders_books(self) -> None:
        xml_path = FIXTURES_DIR / "kindle_sync_metadata.xml"

        asin_list = load_asins_from_xml_path(xml_path)

        self.assertEqual(
            asin_list,
            ["B000000001", "B000000002", "B000000003", "B000000005"],
        )

    def test_get_asin_list_from_kindle_windows_app_xml_uses_store_app_path(
        self,
    ) -> None:
        xml_path = FIXTURES_DIR / "kindle_sync_metadata.xml"

        with tempfile.TemporaryDirectory() as tmp_dir:
            kindle_xml_path = (
                Path(tmp_dir)
                / "Packages/AMZNKindle.AmazonKindleReadingApp_m1sc522ngdk36/LocalState/Classic/Data/Cache/KindleSyncMetadataCache.xml"
            )
            kindle_xml_path.parent.mkdir(parents=True)
            kindle_xml_path.write_text(xml_path.read_text(encoding="utf-8"))

            with unittest.mock.patch.dict("os.environ", {"LOCALAPPDATA": tmp_dir}):
                asin_list = get_asin_list_from_kindle_windows_app_xml()

        self.assertEqual(
            asin_list,
            ["B000000001", "B000000002", "B000000003", "B000000005"],
        )

    def test_load_asins_from_sqlite_path_orders_by_last_access(self) -> None:
        sql_path = FIXTURES_DIR / "bookdata.sql"

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "BookData.sqlite"
            connection = sqlite3.connect(db_path)
            try:
                connection.executescript(sql_path.read_text(encoding="utf-8"))
            finally:
                connection.close()

            asin_list = load_asins_from_sqlite_path(db_path)

        self.assertEqual(asin_list, ["000000003", "000000002", "000000001"])

    def make_web_client(
        self,
        responses: dict[str, FakeWebResponse],
        *,
        page_url: str = "https://read.amazon.co.jp/kindle-library",
    ) -> tuple[
        FakeWebRequest, FakeWebContext, FakeWebChromium, FakeWebPlaywrightManager
    ]:
        request = FakeWebRequest(responses)
        page = FakeWebPage(url=page_url)
        context = FakeWebContext(page, request)
        browser = FakeWebBrowser(context)
        chromium = FakeWebChromium(browser)
        manager = FakeWebPlaywrightManager(FakeWebPlaywright(chromium))
        return request, context, chromium, manager

    def test_web_source_filters_samples_keeps_kindle_unlimited_and_reverses(
        self,
    ) -> None:
        search_url = "https://example.test/search?querySize=50"
        request, context, _, manager = self.make_web_client(
            {
                search_url: FakeWebResponse(
                    web_payload(
                        [
                            web_item("NEWEST-SAMPLE", resource_type="EBOOK_SAMPLE"),
                            web_item("NEWEST-KU", origin_type="KINDLE_UNLIMITED"),
                            web_item("OLDEST"),
                        ]
                    )
                )
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            asins = get_asin_list_from_kindle_web(
                playwright_factory=lambda: manager,
                session_file=Path(tmp_dir) / "amazon-session.json",
                library_url="https://read.amazon.co.jp/kindle-library",
                search_url=search_url,
            )

        self.assertEqual(asins, ["OLDEST", "NEWEST-KU"])
        self.assertEqual(request.get_calls, [search_url])
        self.assertTrue(context.closed)

    def test_web_source_follows_pagination_until_99_and_stops(self) -> None:
        search_url = "https://example.test/search?query=&querySize=50"
        second_url = (
            "https://example.test/search?query=&querySize=50&paginationToken=50"
        )
        first_page = [web_item(f"FIRST-{index:02d}") for index in range(49)]
        second_page = [web_item(f"SECOND-{index:02d}") for index in range(50)]
        request, _, _, manager = self.make_web_client(
            {
                search_url: FakeWebResponse(web_payload(first_page, token="50")),
                second_url: FakeWebResponse(web_payload(second_page, token="100")),
            }
        )

        asins = get_asin_list_from_kindle_web(
            playwright_factory=lambda: manager,
            search_url=search_url,
        )

        self.assertEqual(len(asins), 99)
        self.assertEqual(asins[:3], ["SECOND-49", "SECOND-48", "SECOND-47"])
        self.assertEqual(asins[-3:], ["FIRST-02", "FIRST-01", "FIRST-00"])
        self.assertEqual(request.get_calls, [search_url, second_url])

    def test_web_source_reuses_existing_session(self) -> None:
        search_url = "https://example.test/search"
        request, context, chromium, manager = self.make_web_client(
            {search_url: FakeWebResponse(web_payload([web_item("B1")]))}
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            session_file = Path(tmp_dir) / "amazon-session.json"
            session_file.write_text("{}", encoding="utf-8")
            asins = get_asin_list_from_kindle_web(
                playwright_factory=lambda: manager,
                session_file=session_file,
                search_url=search_url,
                browser_channel="msedge",
            )

        self.assertEqual(asins, ["B1"])
        self.assertEqual(
            chromium.launch_calls, [{"headless": False, "channel": "msedge"}]
        )
        self.assertEqual(
            chromium.browser.new_context_calls[0]["storage_state"], str(session_file)
        )
        self.assertEqual(context.storage_state_paths, [])

    def test_web_source_saves_session_after_manual_login(self) -> None:
        search_url = "https://example.test/search"
        request, context, _, manager = self.make_web_client(
            {search_url: FakeWebResponse(web_payload([web_item("B1")]))},
            page_url="https://www.amazon.co.jp/ap/signin",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            session_file = Path(tmp_dir) / "amazon-session.json"
            asins = get_asin_list_from_kindle_web(
                playwright_factory=lambda: manager,
                session_file=session_file,
                search_url=search_url,
            )

        self.assertEqual(asins, ["B1"])
        self.assertEqual(context.storage_state_paths, [str(session_file)])

    def test_web_source_fails_for_unusable_responses(self) -> None:
        search_url = "https://example.test/search"
        scenarios = [
            (FakeWebResponse(ValueError("invalid JSON")), "could not parse"),
            (FakeWebResponse({}), "missing a list-valued itemsList"),
            (FakeWebResponse({}, ok=False, status=503), "status 503"),
        ]
        for response, message in scenarios:
            with self.subTest(message=message):
                _, _, _, manager = self.make_web_client({search_url: response})
                with self.assertRaisesRegex(RuntimeError, message):
                    get_asin_list_from_kindle_web(
                        playwright_factory=lambda: manager,
                        search_url=search_url,
                    )


if __name__ == "__main__":
    unittest.main()
