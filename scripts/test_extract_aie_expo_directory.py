import unittest
from scripts.extract_aie_expo_directory import parse_page


class ParsePageTests(unittest.TestCase):
    def test_normalizes_and_maps_public_listing(self):
        payload = {"code": 200, "data": {"total": 1, "list": [{"id": 42, "exhiEnCompany": "  Example\u00a0 Labs  ", "exhiCompany": " 示例 公司 ", "boothNo": " A-1 ", "enRegisterAddress": "  Hong Kong  "}]}}
        rows, total = parse_page(payload, scope_id=1588, scope_label="Zhuhai Zone", page=1)
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["company_name"], "Example Labs")
        self.assertEqual(rows[0]["company_name_local"], "示例 公司")
        self.assertEqual(rows[0]["detail_page_url"], "")

    def test_rejects_invalid_envelope(self):
        with self.assertRaisesRegex(ValueError, "unexpected API envelope"):
            parse_page({"code": 403}, scope_id=1, scope_label="test", page=1)

    def test_rejects_missing_name_and_nonzero_empty_page(self):
        with self.assertRaisesRegex(ValueError, "missing stable ID or company name"):
            parse_page({"code": 200, "data": {"total": 1, "list": [{"id": 1}]}}, scope_id=1, scope_label="test", page=1)
        with self.assertRaisesRegex(ValueError, "nonzero total"):
            parse_page({"code": 200, "data": {"total": 1, "list": []}}, scope_id=1, scope_label="test", page=1)


if __name__ == "__main__":
    unittest.main()
