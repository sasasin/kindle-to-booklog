from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree


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

    kindle_xml_path = Path(userprofile) / "AppData/Local/Amazon/Kindle/Cache/KindleSyncMetadataCache.xml"
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

    kindle_sqlite_path = Path(home) / "Library/Containers/com.amazon.Lassen/Data/Library/Protected/BookData.sqlite"
    return load_asins_from_sqlite_path(kindle_sqlite_path)
