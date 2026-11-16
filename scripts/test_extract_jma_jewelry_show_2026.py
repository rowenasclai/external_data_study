import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("extract_jma_jewelry_show_2026.py")
SPEC = importlib.util.spec_from_file_location("jma", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

LISTING = '''<table><thead><tr><th>x</th></tr></thead><tbody>
<tr href="exhibitor_directory_detail.php?id=A1"><td>  A &amp; B<br>公司 </td><td>Hong Kong</td><td>H1</td><td>1</td><td>Fine</td></tr>
</tbody></table>'''

class JmaParserTests(unittest.TestCase):
    def test_listing_preserves_multilingual_name_and_resolves_profile(self):
        rows = MODULE.parse_listing(LISTING)
        self.assertEqual(rows[0]["exhibitor_id"], "A1")
        self.assertEqual(rows[0]["company_name"], "A & B 公司")
        self.assertEqual(rows[0]["profile_url"], "https://www.jewelryshows.org/en/trade/exhibitor_directory_detail.php?id=A1")

    def test_listing_fails_when_required_identity_is_missing(self):
        broken = LISTING.replace("A &amp; B<br>公司", "")
        with self.assertRaises(ValueError):
            MODULE.parse_listing(broken)

    def test_profile_fields_do_not_spill_into_following_rows(self):
        page = '<div class="row"><div class="name">Tel.</div><div class="field">123</div></div><div class="row"><div class="name">Exhibits</div><div class="field">Gems</div></div>'
        self.assertEqual(MODULE.parse_profile(page), {"telephone": "123", "email": "", "website": "", "address": "", "description": "", "activity": "", "products": "Gems", "brands": ""})

    def test_validation_rejects_duplicate_ids(self):
        row = {field: "x" for field in MODULE.FIELDS}
        row["company_name"] = "Example"; row["profile_url"] = "https://example.invalid/1"
        with self.assertRaises(ValueError):
            MODULE.validate([row, row.copy()], 2)

if __name__ == "__main__":
    unittest.main()
