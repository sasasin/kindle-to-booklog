from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from playwright.sync_api import sync_playwright

SESSION_FILE = Path("session.json")
BOOKLOG_INPUT_URL = "https://booklog.jp/input"


def parse_purchase_date(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RuntimeError(f"unexpected purchase_date format: {value}") from exc


# for Windows Kindle app
def get_asin_list_from_kindle_xml() -> list[str]:
    userprofile = os.environ.get("USERPROFILE")
    if not userprofile:
        raise RuntimeError("USERPROFILE is not set")

    kindle_xml_path = Path(userprofile) / "AppData/Local/Amazon/Kindle/Cache/KindleSyncMetadataCache.xml"
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


# for macOS Kindle app
def get_asin_list_from_kindle_sqlite_db() -> list[str]:
    home = os.environ.get("HOME")
    if not home:
        raise RuntimeError("HOME is not set")

    kindle_sqlite_path = Path(home) / "Library/Containers/com.amazon.Lassen/Data/Library/Protected/BookData.sqlite"

    with sqlite3.connect(kindle_sqlite_path) as database:
        cursor = database.execute(
            """
            SELECT substr(zbook.zbookid, 3, 10) AS asin
            FROM zbook
            ORDER BY zbook.zrawlastaccesstime DESC
            LIMIT 99
            """
        )
        asin_list = [row[0] for row in cursor.fetchall()]

    # ASIN だけのリストを作る
    print(asin_list)
    return asin_list


def add_books_to_booklog(asin_list: list[str]) -> None:
    browser_channel = os.environ.get("BROWSER_CHANNEL", "chrome")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, channel=browser_channel)
        # セッションファイルが存在する場合は読み込む
        context_options = {
            "locale": "ja-JP",
            "viewport": {"width": 1280, "height": 800},
        }
        if SESSION_FILE.exists():
            context_options["storage_state"] = str(SESSION_FILE)

        context = browser.new_context(**context_options)

        try:
            page = context.new_page()
            # ログインをスキップして直接 /input へ
            page.goto(BOOKLOG_INPUT_URL)

            # セッション切れまたは初回: ログインページにリダイレクトされた場合
            if not page.url.startswith(BOOKLOG_INPUT_URL):
                print("ブラウザでブクログにログインしてください（reCAPTCHA を解いてログインボタンを押してください）")
                page.wait_for_url(BOOKLOG_INPUT_URL, timeout=300_000)
                # セッションを保存
                context.storage_state(path=str(SESSION_FILE))
                page.goto(BOOKLOG_INPUT_URL)

            textbox = page.get_by_role("textbox", name="ISBN/ASINコード")
            textbox.click()
            # ASINを改行文字\n区切りで列挙する
            textbox.fill("\n".join(asin_list))
            # カテゴリは埋めなくてもいいかな...
            # page.get_by_label("カテゴリ").select_option("1214007")
            # 4=積読
            page.get_by_label("読書状況").select_option("4")
            page.get_by_role("button", name="まとめて登録する").click()
            page.wait_for_url(BOOKLOG_INPUT_URL)
        finally:
            context.close()
            browser.close()


def main() -> int:
    if sys.platform == "win32":
        asin_list = get_asin_list_from_kindle_xml()
    elif sys.platform == "darwin":
        asin_list = get_asin_list_from_kindle_sqlite_db()
    else:
        raise RuntimeError(f"unsupported platform: {sys.platform}")

    # print(asin_list)
    print(len(asin_list))
    print("\n".join(asin_list))

    add_books_to_booklog(asin_list)
    return 0
