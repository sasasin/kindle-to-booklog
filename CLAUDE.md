# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Kindle で購入した書籍を自動でブクログに登録するツール。Python 版の Playwright を使って Chrome を操作し、ブクログの一括登録フォームに ASIN コードを入力する。

## Setup

```bash
uv sync
uv run playwright install chrome
```

## Running the App

```bash
uv run kindle-to-booklog
```

## Running Tests

`tests/` に `unittest` ベースのテストがある。Kindle の実ファイルや `booklog.jp` にはアクセスせず、fixture の XML / SQL と Playwright のフェイク実装で検証する。

```bash
uv run python -m unittest discover -s tests
```

## Architecture

`src/kindle_to_booklog/` に実装本体を置く `src` レイアウトを採用。実行エントリポイントは `kindle_to_booklog.cli:main` で、`uv run kindle-to-booklog` から起動する。

処理フローは以下の3ステップ:

1. **Kindle から ASIN リストを取得** — OS によって異なる2つの実装がある:
   - Windows: `get_asin_list_from_kindle_xml()` — Kindle アプリのキャッシュ XML (`KindleSyncMetadataCache.xml`) をパース
   - macOS: `get_asin_list_from_kindle_sqlite_db()` — Kindle アプリの SQLite DB (`BookData.sqlite`) を `sqlite3` で読み込む
   - 取得対象は購入日の新しい順に最大99冊

2. **ブクログにログイン・登録** — `add_books_to_booklog()` で Playwright の Chromium を headless=false で起動し、ブクログの一括登録フォームに ASIN を改行区切りで入力して登録する。読書状況は「積読」(4) で登録される。

3. **OS 判定** — `sys.platform` で分岐し、適切な取得関数を呼び出す。

## Key Dependencies

- `playwright` — ブラウザ自動操作 (Chromium のみ使用)
- `xml.etree.ElementTree` — Windows 版 Kindle XML のパース
- `sqlite3` — macOS 版 Kindle SQLite DB の読み込み
