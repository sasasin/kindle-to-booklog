from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from kindle_to_booklog import cli


class CliTests(unittest.TestCase):
    def test_main_uses_windows_source(self) -> None:
        fake_factory = object()
        with (
            patch("kindle_to_booklog.cli.sys.platform", "win32"),
            patch(
                "kindle_to_booklog.cli.get_asin_list_from_kindle_xml",
                return_value=["B1", "B2"],
            ) as get_xml,
            patch("kindle_to_booklog.cli.add_books_to_booklog") as add_books,
            patch("kindle_to_booklog.cli.sync_playwright", fake_factory),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            result = cli.main()

        self.assertEqual(result, 0)
        get_xml.assert_called_once_with()
        add_books.assert_called_once()
        self.assertEqual(add_books.call_args.args[0], ["B1", "B2"])
        self.assertIs(add_books.call_args.kwargs["playwright_factory"], fake_factory)
        self.assertIn("2", stdout.getvalue())
        self.assertIn("B1\nB2", stdout.getvalue())

    def test_main_rejects_unsupported_platform(self) -> None:
        with patch("kindle_to_booklog.cli.sys.platform", "linux"):
            with self.assertRaisesRegex(RuntimeError, "unsupported platform: linux"):
                cli.main()


if __name__ == "__main__":
    unittest.main()
