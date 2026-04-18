from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from kindle_to_booklog.kindle import (
    load_asins_from_sqlite_path,
    load_asins_from_xml_path,
    parse_purchase_date,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class KindleTests(unittest.TestCase):
    def test_parse_purchase_date_supports_z_suffix(self) -> None:
        parsed = parse_purchase_date("2024-01-02T03:04:05Z")
        self.assertEqual(parsed.isoformat(), "2024-01-02T03:04:05+00:00")

    def test_load_asins_from_xml_path_filters_and_orders_books(self) -> None:
        xml_path = FIXTURES_DIR / "kindle_sync_metadata.xml"

        asin_list = load_asins_from_xml_path(xml_path)

        self.assertEqual(
            asin_list,
            ["B000000001", "B000000002", "B000000003", "B000000005"],
        )

    def test_load_asins_from_sqlite_path_orders_by_last_access(self) -> None:
        sql_path = FIXTURES_DIR / "bookdata.sql"

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "BookData.sqlite"
            connection = sqlite3.connect(db_path)
            try:
                connection.executescript(sql_path.read_text(encoding="utf-8"))
            finally:
                connection.close()

            asin_list = load_asins_from_sqlite_path(db_path)

        self.assertEqual(asin_list, ["000000003", "000000002", "000000001"])


if __name__ == "__main__":
    unittest.main()
