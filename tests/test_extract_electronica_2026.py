import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.extract_electronica_2026 import EXPECTED_FIELDS, parse_listing, paging_payload, write_outputs  # noqa: E402


class ElectronicaParserTests(unittest.TestCase):
    def test_listing_keeps_public_records_excludes_ad_and_preserves_pagination_metadata(self):
        html = """
        <form id="paging_1">
          <input type="submit" name="SRField" value="2">
          <input type="hidden" name="StartRow_query_res_2" value="16">
          <input type="hidden" name="sb_rpp" value="15">
        </form>
        <div class="pb_ce"><a href="./exhibitordetails/acme/?id=7">  Acme   GmbH </a></div>
        <div class="pb_ce advert"><a href="exhibitordetails/promoted/?id=8">Promoted card</a></div>
        <div class="pb_ce"><a href="/exhibitor-portal/2026/list-of-exhibitors/exhibitordetails/多言語/?id=9">多言語 会社</a></div>
        """
        rows, total, page_count = parse_listing(html)
        self.assertEqual(total, 16)
        self.assertEqual(page_count, 2)
        self.assertEqual([r["company_name"] for r in rows], ["Acme GmbH", "多言語 会社"])
        self.assertEqual(rows[0]["profile_url"], "https://exhibitors.electronica.de/exhibitor-portal/2026/list-of-exhibitors/exhibitordetails/acme/?id=7")
        self.assertEqual(rows[1]["profile_url"], "https://exhibitors.electronica.de/exhibitor-portal/2026/list-of-exhibitors/exhibitordetails/多言語/?id=9")

    def test_listing_deduplicates_same_profile_link_without_deduplicating_names(self):
        html = """
        <a href="/exhibitordetails/acme/?id=7">Acme One</a>
        <a href="/exhibitordetails/acme/?id=7">Acme Duplicate Link</a>
        """
        rows, _, _ = parse_listing(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company_name"], "Acme One")

    def test_outputs_use_identical_field_order_and_unicode(self):
        row = {
            "source_position": 1, "company_name": "多言語会社", "profile_url": "https://exhibitors.electronica.de/profile/1",
            "listing_page": 1, "profile_title": "多言語会社", "profile_description": "Public profile",
            "address": "", "website": "", "profile_sections": "",
        }
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            write_outputs([row], outdir, total=1, page_count=1)
            json_rows = json.loads((outdir / "electronica_2026_exhibitors.json").read_text(encoding="utf-8"))
            with (outdir / "electronica_2026_exhibitors.csv").open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                csv_rows = list(reader)
                self.assertEqual(reader.fieldnames, EXPECTED_FIELDS)
            self.assertEqual(list(json_rows[0]), EXPECTED_FIELDS)
            self.assertEqual(json_rows[0]["company_name"], "多言語会社")
            self.assertEqual({key: str(value) for key, value in json_rows[0].items()}, csv_rows[0])

    def test_paging_payload_preserves_native_fields_and_adds_next_action(self):
        html = """
        <form id="paging_1">
          <input type="hidden" name="StartRow_query_res_1" value="1">
          <input type="submit" name="SRField" value="242">
        </form>
        """
        payload = paging_payload(html)
        self.assertIn(("StartRow_query_res_1", "1"), payload)
        self.assertIn(("SRField_next", "next"), payload)
        self.assertIn(("nvp", "search"), payload)


if __name__ == "__main__":
    unittest.main()
