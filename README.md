# kindle-to-booklog

# これは何

Amazon Kindle で購入した書籍をブクログに登録するやつです。

# インストール

Amazon Kindle アプリをインストールして、ログインしてください。Git Bash, `uv`, Google Chrome など Playwright が対応しているブラウザを何らかの方法でインストールしてください。

その後に以下。

```
$ uv tool install git+https://github.com/sasasin/kindle-to-booklog.git
$ uvx playwright install chrome
```

開発用にリポジトリを clone して実行する場合は以下。

```
$ git clone git@github.com:sasasin/kindle-to-booklog.git
$ cd kindle-to-booklog
$ uv sync
$ uv run playwright install chrome
```

# つかいかた

Amazon Kindle アプリを起動して、同期ボタン押して、書誌情報を最新にしたら、アプリを終了してください。
Amazon Kindle アプリを起動して、同期ボタン押して、書誌情報を最新にしたら、アプリを終了してください。
これでローカルの書誌情報が最新化されます。

※1回目の起動と同期では、書誌情報XMLファイルが最新化されないことがあるようで、2回やればまあ最新になります。

以下を実行してください。Chrome が起動して、Kindle で購入日の新しい99冊をブクログに登録します。

```
$ kindle-to-booklog
```

`BROWSER_CHANNEL` 環境変数でブラウザを指定できます（省略時は `chrome`）。指定できる値は `chrome` / `msedge` など Playwright が対応しているチャンネル名です。

```
# Edge で起動する場合
$ BROWSER_CHANNEL=msedge kindle-to-booklog
```

**初回実行時** はブクログのログインページが表示されます。reCAPTCHA を解いて手動でログインしてください。ログイン成功後にセッションが `session.json` に保存され、次回以降はログイン操作なしで自動実行されます。

セッションの有効期限が切れた場合は、再度ログインページが表示されます。同様に手動でログインしてください。

## Kindle for Web を使う場合

Linux など Kindle デスクトップアプリに対応していない環境では、`--web` を指定すると Kindle for Web のライブラリから直近99冊を取得できます。Windows/macOS でもこのオプションを指定すれば Kindle for Web を使用します。

```
$ kindle-to-booklog --web
```

初回実行時、または Amazon のセッションが切れた場合は、表示されたブラウザで Amazon に手動ログインしてください。CAPTCHA や MFA が表示された場合もブラウザ上で完了します。ログイン後の認証状態は `amazon-session.json` に保存され、次回以降は有効な間は再利用されます。このファイルには認証情報が含まれるため、保護し、共有・コミットしないでください（`.gitignore` で除外されています）。

Web モードでは Kindle for Web の非公開・内部的な検索エンドポイントを利用しています。Amazon の公開APIではなく、将来仕様変更や利用不能になる可能性があります。

# テスト

ローカルの Kindle XML / SQLite や `booklog.jp` に依存しないテストを `tests/` に用意しています。fixture の XML と SQL、Playwright のフェイク実装を使うので、オフラインでも実行できます。

```
$ uv sync --group dev
$ uv run --group dev coverage run -m unittest discover -s tests
$ uv run --group dev coverage report -m
$ uv run --group dev coverage html
$ uv run --group dev coverage xml
```

HTML レポートは `htmlcov/index.html`、XML レポートは `coverage.xml` に出力されます。
