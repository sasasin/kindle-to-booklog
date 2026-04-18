# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Kindle で購入した書籍を自動でブクログに登録するツール。Python 版の Playwright を使って Chrome を操作し、ブクログの一括登録フォームに ASIN コードを入力する。

## Setup

```bash
uv tool install playwright
playwright install chrome
```

## Running the App

```bash
./main.py
```

## Running Tests

自動テストはまだ用意されていない。必要なら `uv run python -m py_compile main.py` などの軽い構文確認から始める。

## Architecture

`main.py` が唯一のエントリポイント。`uv run` 用の shebang と inline script metadata を使用。

処理フローは以下の3ステップ:

1. **Kindle から ASIN リストを取得** — OS によって異なる2つの実装がある:
   - Windows: `getAsinListFromKindleXml()` — Kindle アプリのキャッシュ XML (`KindleSyncMetadataCache.xml`) をパース
   - macOS: `getAsinListFromKindleSqliteDb()` — Kindle アプリの SQLite DB (`BookData.sqlite`) を `sqlite3` で読み込む
   - 取得対象は購入日の新しい順に最大99冊

2. **ブクログにログイン・登録** — `add_books_to_booklog()` で Playwright の Chromium を headless=false で起動し、ブクログの一括登録フォームに ASIN を改行区切りで入力して登録する。読書状況は「積読」(4) で登録される。

3. **OS 判定** — `sys.platform` で分岐し、適切な取得関数を呼び出す。

## Key Dependencies

- `playwright` — ブラウザ自動操作 (Chromium のみ使用)
- `xml.etree.ElementTree` — Windows 版 Kindle XML のパース
- `sqlite3` — macOS 版 Kindle SQLite DB の読み込み
