from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("extract_guangzhou_design_week_2026_exhibitors.py")
SPEC = importlib.util.spec_from_file_location("gzdesignweek_extractor", MODULE_PATH)
assert SPEC and SPEC.loader
extractor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(extractor)


class GuangzhouDesignWeekParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.category = "Soft Furnishing + Home Deco"
        self.payload = {
            "data": [{
                "category": self.category,
                "venue": "Hall A",
                "children": [
                    {"code": "id-1", "company_name": "  Ácme  株式会社 ", "category": self.category, "stand_code": "A1", "logo": None},
                    {"code": "id-2", "company_name": "Example Co", "category": self.category, "stand_code": None, "logo": "https://img.example/logo.png"},
                ],
            }],
        }

    def test_parses_source_fields_and_preserves_missing_profile_or_logo(self):
        rows = extractor.parse_payload(self.payload, expected_counts={self.category: 2})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["company_name"], "Ácme 株式会社")
        self.assertEqual(rows[0]["exhibitor_id"], "id-1")
        self.assertEqual(rows[0]["venue"], "Hall A")
        self.assertEqual(rows[0]["logo_url"], "")
        self.assertEqual(rows[0]["profile_url"], "")
        self.assertEqual(rows[0]["profile_status"], "not_linked_on_source")
        self.assertEqual(rows[1]["stand"], "")

    def test_rejects_missing_stable_id_and_company_name(self):
        bad = {"data": [{"category": self.category, "children": [{"code": "", "company_name": "Acme", "category": self.category}]}]}
        with self.assertRaisesRegex(ValueError, "stable code or name"):
            extractor.parse_payload(bad, expected_counts=None)

    def test_rejects_category_mismatch_and_duplicates(self):
        bad = {"data": [{"category": self.category, "children": [
            {"code": "same", "company_name": "A", "category": self.category},
            {"code": "same", "company_name": "B", "category": self.category},
        ]}]}
        with self.assertRaisesRegex(ValueError, "duplicate stable"):
            extractor.parse_payload(bad, expected_counts=None)
        mismatch = {"data": [{"category": self.category, "children": [
            {"code": "id", "company_name": "A", "category": "Other"},
        ]}]}
        with self.assertRaisesRegex(ValueError, "category mismatch"):
            extractor.parse_payload(mismatch, expected_counts=None)

    def test_rejects_missing_category_data(self):
        with self.assertRaisesRegex(ValueError, "no category list"):
            extractor.parse_payload({}, expected_counts=None)


if __name__ == "__main__":
    unittest.main()
