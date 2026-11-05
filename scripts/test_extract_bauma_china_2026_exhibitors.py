import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_bauma_china_2026_exhibitors import FIELDS, parse_page, readback_validate, validate, write_outputs

VALID = '''<table><tbody><tr><td><a href="/en/exhibition/info/71">  测试  شركة  </a></td><td>Hall A.01</td><td>China</td><td></td></tr></tbody></table><a href="?page=1">1</a><a href="?page=2">2</a>'''


class BaumaParserTests(unittest.TestCase):
    def test_valid_multilingual_row_and_pagination(self):
        rows, pages = parse_page(VALID, "https://example.test/page=1")
        self.assertEqual(pages, 2)
        self.assertEqual(rows[0]["exhibitor_id"], "71")
        self.assertEqual(rows[0]["company_name"], "测试 شركة")
        self.assertEqual(rows[0]["detail_url"], "https://community.b-china.cn/en/exhibition/info/71")

    def test_missing_tbody_fails(self):
        with self.assertRaisesRegex(ValueError, "table body"):
            parse_page("<html></html>", "https://example.test")

    def test_missing_name_fails(self):
        page = VALID.replace("  测试  شركة  ", "")
        with self.assertRaisesRegex(ValueError, "company name"):
            parse_page(page, "https://example.test")

    def test_missing_id_fails(self):
        with self.assertRaisesRegex(ValueError, "detail ID"):
            parse_page(VALID.replace("/en/exhibition/info/71", "/other"), "https://example.test")

    def test_duplicate_and_missing_page_fail(self):
        rows, _ = parse_page(VALID, "https://example.test")
        duplicate = rows + [dict(rows[0])]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate(duplicate, 1, [1])
        with self.assertRaisesRegex(ValueError, "missing"):
            validate(rows, 2, [1])

    def test_csv_json_equivalence(self):
        rows, _ = parse_page(VALID, "https://example.test")
        rows[0]["source_position"] = "1"
        with tempfile.TemporaryDirectory() as temporary:
            csv_path = Path(temporary) / "out.csv"
            json_path = Path(temporary) / "out.json"
            write_outputs(rows, csv_path, json_path)
            readback_validate(csv_path, json_path, 1)
            self.assertEqual(list(rows[0]), list(FIELDS))


if __name__ == "__main__":
    unittest.main()
