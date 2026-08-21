#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("ai_extract_cioe_exhibitors.py")
SPEC = importlib.util.spec_from_file_location("ai_extract_cioe_exhibitors", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CIOEParserTests(unittest.TestCase):
    def test_parse_listing_response(self) -> None:
        payload = """
        <li><a href="/jtycn/zsen123.html"><img src="/File/logo.png">
        <h3 class="title"> Example   Optics Ltd. </h3>
        <dl><dt>Exhibition Area：</dt><dd>Precision Optics</dd></dl>
        <dl><dt>Hall：</dt><dd>HALL 1</dd></dl>
        <dl><dt>Booth No：</dt><dd>1A01</dd></dl>
        <dl><dt>Main products：</dt><dd>Lens\n systems</dd></dl></a></li>
        !@#$%^&*<span>Total:1</span>
        """
        rows, total = MODULE.parse_listing_response(payload)
        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["exhibitor_id"], "123")
        self.assertEqual(rows[0]["company_name"], "Example Optics Ltd.")
        self.assertEqual(rows[0]["booth_no"], "1A01")
        self.assertEqual(rows[0]["main_products"], "Lens systems")
        self.assertEqual(rows[0]["detail_url"], "https://exhibitors.cioe.cn/jtycn/zsen123.html")

    def test_missing_separator_is_fail_visible(self) -> None:
        with self.assertRaisesRegex(ValueError, "separator"):
            MODULE.parse_listing_response("<li>bad response</li>")

    def test_validation_rejects_duplicate_ids(self) -> None:
        row = {
            "exhibitor_id": "123",
            "company_name": "Example",
        }
        with self.assertRaisesRegex(ValueError, "duplicate"):
            MODULE.validate_rows([dict(row), dict(row)], 2)

    def test_validation_rejects_count_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            MODULE.validate_rows([], 1)


if __name__ == "__main__":
    unittest.main()
