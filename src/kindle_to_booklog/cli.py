import sys

from playwright.sync_api import sync_playwright

from kindle_to_booklog.booklog import add_books_to_booklog
from kindle_to_booklog.kindle import (
    get_asin_list_from_kindle_sqlite_db,
    get_asin_list_from_kindle_xml,
)


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

    add_books_to_booklog(asin_list, playwright_factory=sync_playwright)
    return 0
