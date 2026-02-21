# kindle-to-booklog

# これは何

Amazon Kindle で購入した書籍をブクログに登録するやつです。

# インストール

Amazon Kindle アプリをインストールして、ログインしてください。 Git, Node.js, Google Chrome など Playwright が対応しているブラウザを何らかの方法でインストールしてください。

その後に以下。

```
$ git clone git@github.com:sasasin/kindle-to-booklog.git
$ npm install
$ npx playwright install
```

# つかいかた

Amazon Kindle アプリを起動して、同期ボタン押して、書誌情報を最新にしたら、アプリを終了してください。
Amazon Kindle アプリを起動して、同期ボタン押して、書誌情報を最新にしたら、アプリを終了してください。
これでローカルの書誌情報が最新化されます。

※1回目の起動と同期では、書誌情報XMLファイルが最新化されないことがあるようで、2回やればまあ最新になります。

以下を実行してください。Chrome が起動して、Kindle で購入日の新しい99冊をブクログに登録します。

```
$ cd kindle-to-booklog
$ node app/main.js
```

`BROWSER_CHANNEL` 環境変数でブラウザを指定できます（省略時は `chrome`）。指定できる値は `chrome` / `msedge` など Playwright が対応しているチャンネル名です。

```
# Edge で起動する場合
$ BROWSER_CHANNEL=msedge node app/main.js
```

**初回実行時** はブクログのログインページが表示されます。reCAPTCHA を解いて手動でログインしてください。ログイン成功後にセッションが `session.json` に保存され、次回以降はログイン操作なしで自動実行されます。

セッションの有効期限が切れた場合は、再度ログインページが表示されます。同様に手動でログインしてください。
