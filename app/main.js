import { readFileSync, existsSync } from 'node:fs';
import xml2js from 'xml2js';
import Database from 'better-sqlite3';
import { chromium } from 'playwright';

const SESSION_FILE = 'session.json';

// for Windows Kindle app
const getAsinListFromKindleXml = async() => {

  const KINDLE_XML_PATH = process.env.USERPROFILE + "\\AppData\\Local\\Amazon\\Kindle\\Cache\\KindleSyncMetadataCache.xml";
  console.log(KINDLE_XML_PATH);
  const xml = readFileSync(KINDLE_XML_PATH, "utf-8");
  const parser = new xml2js.Parser({
    async: false,
    explicitArray: false
  });
  let jsonData;
  parser.parseString(xml, function (err, result) {
    jsonData = result;
  });

  let books = jsonData.response.add_update_list.meta_data;
  console.log(books.length);
  // 購入日が空の本は除外する
  books = books.filter((book) => book.purchase_date != "");
  console.log(books.length);
  // 購入日の、新しい本が先頭、古い本が末尾に来るよう並べる
  books.sort( (a,b) => Date.parse(b.purchase_date) - Date.parse(a.purchase_date));
  console.log(books.length);
  // 購入日の新しい99冊だけ残す
  books = books.toSpliced(99)
  // 購入日の、古い本が先頭、新しい本が末尾に来るよう並べる
  books.sort( (a,b) => Date.parse(a.purchase_date) - Date.parse(b.purchase_date));
  //console.log(JSON.stringify(books, null, 2));

  // ASIN だけのリストを作る
  const AsinList = [];
  books.forEach(book => {
    AsinList.push(book.ASIN);
  });

  return AsinList;
}

// for macOS Kindle app
const getAsinListFromKindleSqliteDB = async() => {

  const KINDLE_SQLITE3_PATH = process.env.HOME + '/Library/Containers/com.amazon.Lassen/Data/Library/Protected/BookData.sqlite';

  const database = new Database(KINDLE_SQLITE3_PATH);
  database.pragma('journal_mode = WAL');

  const statement = database.prepare('SELECT substring(zbook.zbookid, 3, 10) as ASIN FROM zbook ORDER BY zbook.zrawlastaccesstime DESC LIMIT 99');

  const books = statement.all();

  // ASIN だけのリストを作る
  const AsinList = [];
  books.forEach(book => {
    AsinList.push(book.ASIN);
  });

  console.log(AsinList);

  return AsinList;
}

const addBooksToBooklog = async (AsinList) => {
  const browser = await chromium.launch({
    headless: false
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto('https://booklog.jp/logout');
  await page.getByRole('link', { name: 'ログイン', exact: true }).click();
  await page.waitForURL('https://booklog.jp/login')
  await page.getByRole('textbox', { name: 'ブクログID' }).click();
  await page.getByRole('textbox', { name: 'ブクログID' }).fill(BOOKLOG_ID);
  await page.getByRole('textbox', { name: 'パスワード' }).click();
  await page.getByRole('textbox', { name: 'パスワード' }).fill(BOOKLOG_PASSWORD);

  await page.getByRole('button', { name: 'ログイン' }).click();
  await page.waitForURL('https://booklog.jp/home')

  await page.goto('https://booklog.jp/input');
  await page.getByRole('textbox', { name: 'ISBN/ASINコード' }).click();
  // ASINを改行文字\n区切りで列挙する
  await page.getByRole('textbox', { name: 'ISBN/ASINコード' }).fill(AsinList.join('\n'));
  // カテゴリは埋めなくてもいいかな...
  //await page.getByLabel('カテゴリ').selectOption('1214007');
  // 4=積読
  await page.getByLabel('読書状況').selectOption('4');
  await page.getByRole('button', { name: 'まとめて登録する' }).click();
  await page.waitForURL('https://booklog.jp/input');

  await context.close();
  await browser.close();
}

const AsinList =
  (process.platform === 'win32')
  ? await getAsinListFromKindleXml()
  : await getAsinListFromKindleSqliteDB();

//console.log(AsinList);
console.log(AsinList.length);
console.log(AsinList.join('\n'));

await addBooksToBooklog(AsinList);
