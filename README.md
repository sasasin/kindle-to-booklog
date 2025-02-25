# kindle-to-booklog

# これは何

Amazon Kindle で購入した書籍をブクログに登録するやつです。

# インストール

Amazon Kindle アプリをインストールして、ログインしてください。 Git, Node.js を何らかの方法でインストールしてください。

その後に以下。

```
$ git clone git@github.com:sasasin/kindle-to-booklog.git
$ npm install
```

# つかいかた

Amazon Kindle アプリを起動して、同期ボタン押して、書誌情報を最新にしたら、アプリを終了してください。
Amazon Kindle アプリを起動して、同期ボタン押して、書誌情報を最新にしたら、アプリを終了してください。
これでローカルの書誌情報が最新化されます。

※1回目の起動と同期では、書誌情報XMLファイルが最新化されないことがあるようで、2回やればまあ最新になります。

環境変数にブクログのログイン情報を設定してから実行してください。Chrome が起動して、ブクログにログインして、Kindle で購入日の新しい99冊をブクログに登録します。

```
$ export BOOKLOG_ID="xxxxxxxx"
$ export BOOKLOG_PASSWORD="yyyyyyyyyyyyy"
$ cd kindle-to-booklog
$ node app/main.js
```

ブクログのログイン画面で稀に止まりますが、Chrome に表示されてるログインボタンを押してやると自動操作が進むことがあります。止まったままだったら、 Chrome を閉じて `node app/main.js` を再実行してください。

短時間に複数回など高頻度に実行すると、ブクログにログインするとき「不正な操作が検知された」として止まることがあります。頻度を下げて使ってください。こちらも同様に Chrome に表示されてるログインボタンを押してやると自動操作が進むことがあります。止まったままだったら、 Chrome を閉じて `node app/main.js` を再実行してください。
