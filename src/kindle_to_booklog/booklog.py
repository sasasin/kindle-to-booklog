from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

SESSION_FILE = Path("session.json")
BOOKLOG_INPUT_URL = "https://booklog.jp/input"


class PlaywrightFactory(Protocol):
    def __call__(self): ...


def add_books_to_booklog(
    asin_list: list[str],
    *,
    playwright_factory: PlaywrightFactory,
    session_file: Path = SESSION_FILE,
    booklog_input_url: str = BOOKLOG_INPUT_URL,
    browser_channel: str | None = None,
) -> None:
    channel = browser_channel or os.environ.get("BROWSER_CHANNEL", "chrome")

    with playwright_factory() as playwright:
        browser = playwright.chromium.launch(headless=False, channel=channel)
        # セッションファイルが存在する場合は読み込む
        context_options = {
            "locale": "ja-JP",
            "viewport": {"width": 1280, "height": 800},
        }
        if session_file.exists():
            context_options["storage_state"] = str(session_file)

        context = browser.new_context(**context_options)

        try:
            page = context.new_page()
            # ログインをスキップして直接 /input へ
            page.goto(booklog_input_url)

            # セッション切れまたは初回: ログインページにリダイレクトされた場合
            if not page.url.startswith(booklog_input_url):
                print("ブラウザでブクログにログインしてください（reCAPTCHA を解いてログインボタンを押してください）")
                page.wait_for_url(booklog_input_url, timeout=300_000)
                # セッションを保存
                context.storage_state(path=str(session_file))
                page.goto(booklog_input_url)

            textbox = page.get_by_role("textbox", name="ISBN/ASINコード")
            textbox.click()
            # ASINを改行文字\n区切りで列挙する
            textbox.fill("\n".join(asin_list))
            # カテゴリは埋めなくてもいいかな...
            # page.get_by_label("カテゴリ").select_option("1214007")
            # 4=積読
            page.get_by_label("読書状況").select_option("4")
            page.get_by_role("button", name="まとめて登録する").click()
            page.wait_for_url(booklog_input_url)
        finally:
            context.close()
            browser.close()
