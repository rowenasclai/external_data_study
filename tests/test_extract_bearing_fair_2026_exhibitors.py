import unittest

from scripts.extract_bearing_fair_2026_exhibitors import ExtractionError, parse_detail, parse_listing, validate


class BearingParserTests(unittest.TestCase):
    def test_listing_and_detail(self):
        listing = '''<h4 class="pg-blog-item-title"><a href="/eindex.php/index/view/id/1.html">BEARING 2026 EXHIBITORS LIST 1</a></h4>
        <h4 class="pg-blog-item-title"><a href="/eindex.php/index/view/id/2.html">BEARING 2026 EXHIBITORS LIST 2</a></h4>'''
        self.assertEqual(parse_listing(listing), [(1, "http://www.bearingfair.cn/eindex.php/index/view/id/1.html"), (2, "http://www.bearingfair.cn/eindex.php/index/view/id/2.html")])
        page = '''<div class="pg-blog-item blog-details text-center"><p>3HA001 示例公司 EXAMPLE COMPANY</p></div><div class="col-xl-3">'''
        rows = parse_detail(page, 1, "https://example.test/1")
        self.assertEqual(rows[0]["exhibitor_id"], "1:3HA001:示例公司 EXAMPLE COMPANY")
        self.assertEqual(rows[0]["company_name_zh"], "示例公司 EXAMPLE COMPANY")

    def test_rejects_gap_duplicate_and_missing_name(self):
        with self.assertRaises(ExtractionError):
            parse_listing('<h4 class="pg-blog-item-title"><a href="/a">BEARING 2026 EXHIBITORS LIST 2</a></h4>')
        rows = [
            {"exhibitor_id": "A1", "booth": "A1", "company_name_zh": "甲", "detail_url": "u", "source_group": "1"},
            {"exhibitor_id": "A1", "booth": "A1", "company_name_zh": "乙", "detail_url": "u", "source_group": "1"},
        ]
        with self.assertRaises(ExtractionError):
            validate(rows, [1])

    def test_rejects_unparsable_source_row(self):
        page = '''<div class="pg-blog-item blog-details text-center"><p>not a booth record</p></div><div class="col-xl-3">'''
        with self.assertRaises(ExtractionError):
            parse_detail(page, 1, "https://example.test/1")


if __name__ == "__main__":
    unittest.main()
