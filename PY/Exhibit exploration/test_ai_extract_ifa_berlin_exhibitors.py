from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("ai_extract_ifa_berlin_exhibitors.py")
SPEC = importlib.util.spec_from_file_location("ai_extract_ifa_berlin_exhibitors", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class IFAParserTests(unittest.TestCase):
    def test_parse_listing_and_normalize_multiple_locations(self) -> None:
        payload = """
        <div class="brand-card"><a class="list-item-link" href="/exhibitors/example">
        <div><img src="/logo.png"><div class="name"> Example   Technology </div>
        <div class="chip show-area">Smart Home</div><div class="brand-location-hall">Hall 1.1</div>
        <div class="brand-location-stand">H1.1-001</div><div class="country">Germany</div></div></a>
        <button data-entity-id="42"></button></div>
        <a href="?page=1">1</a><a href="?page=2">2</a>
        """
        rows, pages = MODULE.parse_listing(payload, "https://www.ifa-berlin.com/exhibitors")
        self.assertEqual(pages, 2)
        self.assertEqual(rows[0]["exhibitor_id"], "42")
        self.assertEqual(rows[0]["company_name"], "Example Technology")
        self.assertEqual(rows[0]["show_areas"], "Smart Home")
        self.assertEqual(rows[0]["halls"], "Hall 1.1")
        self.assertEqual(rows[0]["booths"], "H1.1-001")
        self.assertEqual(rows[0]["detail_url"], "https://www.ifa-berlin.com/exhibitors/example")

    def test_missing_pagination_is_fail_visible(self) -> None:
        payload = """
        <div class="brand-card"><a class="list-item-link" href="/exhibitors/example">
        <div class="name">Example</div></a><button data-entity-id="42"></button></div>
        """
        with self.assertRaisesRegex(ValueError, "pagination"):
            MODULE.parse_listing(payload, MODULE.SOURCE_URL)

    def test_profile_parser_extracts_description_and_website(self) -> None:
        payload = """
        <div class="brand-detail-header-text gray"><small>Example Technology GmbH</small></div>
        <div class="social-link-text"><a href="https://www.example.com/">example.com</a></div>
        <div class="social-link-text"><a href="https://twitter.com/example">twitter</a></div>
        <div class="description">Example <strong>company</strong><br> profile.</div>
        """
        legal_name, description, website = MODULE.parse_profile(payload)
        self.assertEqual(legal_name, "Example Technology GmbH")
        self.assertEqual(description, "Example company profile.")
        self.assertEqual(website, "https://www.example.com/")

    def test_write_outputs_round_trip(self) -> None:
        row = {field: "" for field in MODULE.FIELDS}
        row.update({"exhibitor_id": "42", "company_name": "Example", "source_position": "1"})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            MODULE.write_outputs([row], root / "result.csv", root / "result.json")
            self.assertTrue((root / "result.csv").is_file())
            self.assertTrue((root / "result.json").is_file())


if __name__ == "__main__":
    unittest.main()
