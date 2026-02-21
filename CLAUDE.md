# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Kindle で購入した書籍を自動でブクログに登録するツール。Playwright を使って Chrome を操作し、ブクログの一括登録フォームに ASIN コードを入力する。

## Setup

```bash
npm install
npx playwright install
```

## Running the App

環境変数にブクログのログイン情報を設定してから実行する:

```bash
export BOOKLOG_ID="xxxxxxxx"
export BOOKLOG_PASSWORD="yyyyyyyyyyyyy"
node app/main.js
```

## Running Tests

```bash
npx playwright test
# 単一テストファイルの実行
npx playwright test tests/example.spec.js
# UIモードで実行
npx playwright test --ui
```

## Architecture

`app/main.js` が唯一のエントリポイント。ES Modules (`"type": "module"`) を使用。

処理フローは以下の3ステップ:

1. **Kindle から ASIN リストを取得** — OS によって異なる2つの実装がある:
   - Windows: `getAsinListFromKindleXml()` — Kindle アプリのキャッシュ XML (`KindleSyncMetadataCache.xml`) をパース
   - macOS: `getAsinListFromKindleSqliteDB()` — Kindle アプリの SQLite DB (`BookData.sqlite`) を `better-sqlite3` で読み込む
   - 取得対象は購入日の新しい順に最大99冊

2. **ブクログにログイン・登録** — `addBooksToBooklog()` で Playwright の Chromium を headless=false で起動し、ブクログの一括登録フォームに ASIN を改行区切りで入力して登録する。読書状況は「積読」(4) で登録される。

3. **OS 判定** — `process.platform === 'win32'` で分岐し、適切な取得関数を呼び出す。

## Key Dependencies

- `@playwright/test` — ブラウザ自動操作 (Chromium のみ使用)
- `xml2js` — Windows 版 Kindle XML のパース
- `better-sqlite3` — macOS 版 Kindle SQLite DB の読み込み