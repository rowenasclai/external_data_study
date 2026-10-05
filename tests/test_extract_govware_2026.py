import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "PY" / "Exhibit exploration" / "extract_govware_2026.py"
spec = importlib.util.spec_from_file_location("govware", MODULE)
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load GovWare extractor module")
govware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(govware)


class GovWareListingParserTests(unittest.TestCase):
    def test_parses_invented_row_and_total(self):
        document = '''<div class="js-librarylistwrapper" data-totalcount="1"><li class="m-exhibitors-list__items__item m-exhibitors-list__items__item--status-sponsor-gold" data-content-i-d="demo-1"><div class="m-exhibitors-list__items__item__image" style="background-image:url('https://example.test/logo.png')"></div><h2 class="m-exhibitors-list__items__item__header__title"><a href="javascript:openRemoteModal('exhibitors/demo','ajax')"> Example Co </a></h2><div class="m-exhibitors-list__items__item__header__meta__stand"> Booth: A01 </div></li></div>'''
        rows, total = govware.parse_listing(document)
        self.assertEqual(total, 1)
        self.assertEqual(rows, [{"exhibitor_id": "demo-1", "company_name": "Example Co", "booth": "A01", "profile_path": "exhibitors/demo", "logo_url": "https://example.test/logo.png", "sponsorship_tier": "Sponsor Gold"}])

    def test_rejects_reported_total_mismatch(self):
        with self.assertRaises(ValueError):
            govware.parse_listing('<div data-totalcount="1"></div>')


if __name__ == "__main__":
    unittest.main()
