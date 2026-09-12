from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

from playwright.sync_api import sync_playwright


AMAZON_SESSION_FILE = Path("amazon-session.json")
KINDLE_WEB_LIBRARY_URL = "https://read.amazon.co.jp/kindle-library"
KINDLE_WEB_SEARCH_URL = (
    "https://read.amazon.co.jp/kindle-library/search"
    "?query=&libraryType=BOOKS&sortType=acquisition_desc&querySize=50"
)
KINDLE_WEB_MAX_ASINS = 99
KINDLE_WEB_LOGIN_TIMEOUT_MS = 300_000
_KINDLE_WEB_LIBRARY_URL_PATTERN = re.compile(
    r"^https://read\.amazon\.co\.jp/kindle-library(?:[/?#]|$)"
)
_AMAZON_LOGIN_URL_PATTERN = re.compile(r"/(?:ap/)?(?:signin|sign-in|login)", re.I)


def parse_purchase_date(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RuntimeError(f"unexpected purchase_date format: {value}") from exc


def load_asins_from_xml_path(kindle_xml_path: Path) -> list[str]:
    print(kindle_xml_path)

    root = ElementTree.fromstring(kindle_xml_path.read_text(encoding="utf-8"))
    books = root.findall("./add_update_list/meta_data")
    print(len(books))

    # 購入日が空の本は除外する
    filtered_books: list[tuple[datetime, str]] = []
    for book in books:
        purchase_date = (book.findtext("purchase_date") or "").strip()
        asin = (book.findtext("ASIN") or "").strip()
        if not purchase_date or not asin:
            continue
        filtered_books.append((parse_purchase_date(purchase_date), asin))

    print(len(filtered_books))
    # 購入日の、新しい本が先頭、古い本が末尾に来るよう並べる
    filtered_books.sort(key=lambda book: book[0], reverse=True)
    print(len(filtered_books))
    # 購入日の新しい99冊だけ残す
    filtered_books = filtered_books[:99]
    # 購入日の、古い本が先頭、新しい本が末尾に来るよう並べる
    filtered_books.sort(key=lambda book: book[0])
    # print(filtered_books)

    # ASIN だけのリストを作る
    return [asin for _, asin in filtered_books]


# for Windows Kindle app
def get_asin_list_from_kindle_xml() -> list[str]:
    userprofile = os.environ.get("USERPROFILE")
    if not userprofile:
        raise RuntimeError("USERPROFILE is not set")

    kindle_xml_path = (
        Path(userprofile)
        / "AppData/Local/Amazon/Kindle/Cache/KindleSyncMetadataCache.xml"
    )
    return load_asins_from_xml_path(kindle_xml_path)


# for Windows Kindle app distributed from Microsoft Store
def get_asin_list_from_kindle_windows_app_xml() -> list[str]:
    localappdata = os.environ.get("LOCALAPPDATA")
    if not localappdata:
        raise RuntimeError("LOCALAPPDATA is not set")

    kindle_xml_path = (
        Path(localappdata)
        / "Packages/AMZNKindle.AmazonKindleReadingApp_m1sc522ngdk36/LocalState/Classic/Data/Cache/KindleSyncMetadataCache.xml"
    )
    return load_asins_from_xml_path(kindle_xml_path)


def load_asins_from_sqlite_path(kindle_sqlite_path: Path) -> list[str]:
    database = sqlite3.connect(kindle_sqlite_path)
    try:
        cursor = database.execute(
            """
            SELECT substr(zbook.zbookid, 3, 10) AS asin
            FROM zbook
            ORDER BY zbook.zrawlastaccesstime DESC
            LIMIT 99
            """
        )
        asin_list = [row[0] for row in cursor.fetchall()]
    finally:
        database.close()

    # ASIN だけのリストを作る
    print(asin_list)
    return asin_list


# for macOS Kindle app
def get_asin_list_from_kindle_sqlite_db() -> list[str]:
    home = os.environ.get("HOME")
    if not home:
        raise RuntimeError("HOME is not set")

    kindle_sqlite_path = (
        Path(home)
        / "Library/Containers/com.amazon.Lassen/Data/Library/Protected/BookData.sqlite"
    )
    return load_asins_from_sqlite_path(kindle_sqlite_path)


def _is_amazon_login_url(url: str) -> bool:
    return bool(_AMAZON_LOGIN_URL_PATTERN.search(url))


def _search_url_with_pagination_token(url: str, token: str) -> str:
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["paginationToken"] = token
    return urlunsplit(parsed._replace(query=urlencode(query)))


def _parse_kindle_web_response(
    response: Any, *, url: str
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(
            f"could not parse Kindle for Web response as JSON: {url}"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"unexpected Kindle for Web response shape (expected an object): {url}"
        )

    items = payload.get("itemsList")
    if not isinstance(items, list):
        raise RuntimeError(
            f"Kindle for Web response is missing a list-valued itemsList: {url}"
        )

    parsed_items: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"unexpected Kindle for Web item at index {index}: expected an object"
            )
        asin = item.get("asin")
        resource_type = item.get("resourceType")
        if not isinstance(asin, str) or not asin:
            raise RuntimeError(
                f"Kindle for Web item at index {index} is missing a valid asin"
            )
        if not isinstance(resource_type, str) or not resource_type:
            raise RuntimeError(
                f"Kindle for Web item at index {index} is missing a valid resourceType"
            )
        parsed_items.append(item)

    token = payload.get("paginationToken")
    if token is not None and (not isinstance(token, str) or not token):
        raise RuntimeError("unexpected Kindle for Web paginationToken")

    return parsed_items, token


def get_asin_list_from_kindle_web(
    *,
    playwright_factory: Any | None = None,
    session_file: Path = AMAZON_SESSION_FILE,
    library_url: str = KINDLE_WEB_LIBRARY_URL,
    search_url: str = KINDLE_WEB_SEARCH_URL,
    browser_channel: str | None = None,
) -> list[str]:
    """Return the 99 most recent non-sample Kindle for Web ASINs.

    Kindle for Web's library search endpoint is an internal Amazon endpoint,
    so response shape errors are deliberately raised instead of treated as an
    empty library.
    """
    channel = browser_channel or os.environ.get("BROWSER_CHANNEL", "chrome")
    playwright_factory = playwright_factory or sync_playwright

    with playwright_factory() as playwright:
        browser = playwright.chromium.launch(headless=False, channel=channel)
        context_options: dict[str, Any] = {
            "locale": "ja-JP",
            "viewport": {"width": 1280, "height": 800},
        }
        if session_file.exists():
            context_options["storage_state"] = str(session_file)

        context = browser.new_context(**context_options)
        try:
            page = context.new_page()
            try:
                page.goto(library_url)
            except Exception as exc:
                raise RuntimeError(
                    f"could not open Kindle for Web library: {library_url}"
                ) from exc

            if _is_amazon_login_url(page.url):
                print(
                    "ブラウザで Amazon にログインしてください（CAPTCHA/MFA が表示された場合も手動で完了してください）"
                )
                try:
                    page.wait_for_url(
                        _KINDLE_WEB_LIBRARY_URL_PATTERN,
                        timeout=KINDLE_WEB_LOGIN_TIMEOUT_MS,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        "Amazon login did not complete for Kindle for Web"
                    ) from exc
                context.storage_state(path=str(session_file))

            request = getattr(context, "request", None)
            if request is None:
                raise RuntimeError(
                    "Playwright context does not provide an API request client"
                )

            asin_list_descending: list[str] = []
            page_url = search_url
            seen_pagination_tokens: set[str] = set()
            while len(asin_list_descending) < KINDLE_WEB_MAX_ASINS:
                try:
                    response = request.get(page_url)
                except Exception as exc:
                    raise RuntimeError(
                        f"could not retrieve Kindle for Web library response: {page_url}"
                    ) from exc

                if not response.ok:
                    raise RuntimeError(
                        f"Kindle for Web library request failed with status "
                        f"{response.status}: {page_url}"
                    )

                items, pagination_token = _parse_kindle_web_response(
                    response, url=page_url
                )
                for item in items:
                    if item["resourceType"] != "EBOOK_SAMPLE":
                        asin_list_descending.append(item["asin"])
                        if len(asin_list_descending) == KINDLE_WEB_MAX_ASINS:
                            break

                if len(asin_list_descending) >= KINDLE_WEB_MAX_ASINS:
                    break
                if pagination_token is None:
                    break
                if pagination_token in seen_pagination_tokens:
                    raise RuntimeError("Kindle for Web paginationToken did not advance")
                seen_pagination_tokens.add(pagination_token)
                page_url = _search_url_with_pagination_token(
                    search_url, pagination_token
                )

            return list(reversed(asin_list_descending[:KINDLE_WEB_MAX_ASINS]))
        finally:
            context.close()
            browser.close()
