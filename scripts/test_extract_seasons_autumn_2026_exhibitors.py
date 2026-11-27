#!/usr/bin/env python3
import unittest

from scripts.extract_seasons_autumn_2026_exhibitors import LANDING_URL, parse_payload, validate


class SeasonsParserTests(unittest.TestCase):
    def payload(self):
        return {
            "recordsTotal": 2,
            "data": [
                {"ExhibitorID": 101, "ExhibitorNameEn": "  Étoile  Co.  ", "StandNoStr": "A01", "CountryEn": "France", "FriendlyUrl": "etoile", "ProductCategoryEn": "Zeta, Alpha"},
                {"ExhibitorID": 102, "ExhibitorNameCht": "測試公司", "StandNoStr": "B02", "CountryEn": "Hong Kong", "FriendlyUrl": "test"},
            ],
        }

    def test_valid_multilingual_payload(self):
        rows, total = parse_payload(self.payload())
        validate(rows, total)
        self.assertEqual(rows[0]["company_name"], "Étoile  Co.")
        self.assertEqual(rows[0]["product_categories"], "Alpha,Zeta")
        self.assertEqual(rows[1]["company_name"], "測試公司")
        self.assertEqual(rows[0]["detail_page_url"], f"{LANDING_URL}/exhibitor/101/etoile")

    def test_count_mismatch_fails(self):
        payload = self.payload()
        payload["recordsTotal"] = 3
        rows, total = parse_payload(payload)
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            validate(rows, total)

    def test_duplicate_or_missing_identity_fails(self):
        payload = self.payload()
        payload["data"][1]["ExhibitorID"] = 101
        rows, total = parse_payload(payload)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate(rows, total)
        payload = self.payload()
        payload["data"][1]["ExhibitorNameCht"] = ""
        rows, total = parse_payload(payload)
        with self.assertRaisesRegex(ValueError, "missing company"):
            validate(rows, total)

    def test_malformed_payload_fails(self):
        with self.assertRaisesRegex(ValueError, "data list"):
            parse_payload({"recordsTotal": 1})


if __name__ == "__main__":
    unittest.main()
