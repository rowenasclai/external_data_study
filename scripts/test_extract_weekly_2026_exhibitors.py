#!/usr/bin/env python3
"""Offline parser/invariant tests for the weekly 2026 public directories."""
from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec); assert spec.loader
    spec.loader.exec_module(module); return module

super_terminal = load("extract_super_terminal_expo_2026")
prowine = load("extract_prowine_shanghai_2026")

class SuperTerminalParserTests(unittest.TestCase):
    def test_valid_and_multilingual_record(self):
        rows, total = super_terminal.parse_page({"recordsTotal": 1, "data": [{"ExhibitorID": 42, "ExhibitorNameEn": "  Ácme  株式会社 ", "StandNoStr": " A1 ", "CountryEn": "Japan", "FriendlyUrl": "acme"}]})
        self.assertEqual(total, 1); self.assertEqual(rows[0]["company_name"], "Ácme 株式会社")
        self.assertEqual(rows[0]["profile_url"], super_terminal.LANDING_URL + "/en-US/exhibitor/acme")
        super_terminal.validate(rows, 1, [0])

    def test_rejects_missing_id_or_name_and_duplicate(self):
        with self.assertRaises(ValueError): super_terminal.parse_page({"recordsTotal": 1, "data": [{"ExhibitorID": "", "ExhibitorNameEn": "A"}]})
        rows = [{"exhibitor_id": "1", "company_name": "A"}, {"exhibitor_id": "1", "company_name": "B"}]
        with self.assertRaises(ValueError): super_terminal.validate(rows, 2, [0])

class ProWineParserTests(unittest.TestCase):
    def test_valid_card_and_metadata(self):
        document = '''<option value="Spain">Spain(1)</option><a href="?expo_id=8&amp;page=1"></a><li class="DemoonstrationList"><strong class="DemoonstrationList-name">  Cuvée &amp; Co  </strong><span class="DemoonstrationList-Country">Country：France</span><span class="DemoonstrationList-Booth">Booth No.：W1-1</span></li>'''
        rows = prowine.parse_page(document)
        self.assertEqual(rows[0]["company_name"], "Cuvée & Co")
        self.assertEqual(rows[0]["exhibitor_key"], "France|W1-1|Cuvée & Co")
        self.assertEqual(prowine.metadata(document), (1, 1))
        prowine.validate(rows, 1, [1], 1)

    def test_rejects_missing_card_fields_duplicate_and_missing_page(self):
        with self.assertRaises(ValueError): prowine.parse_page('<li class="DemoonstrationList">bad</li>')
        rows = [{"exhibitor_key": "same", "company_name": "A"}, {"exhibitor_key": "same", "company_name": "A"}]
        with self.assertRaises(ValueError): prowine.validate(rows, 2, [1], 2)

if __name__ == "__main__":
    unittest.main()
