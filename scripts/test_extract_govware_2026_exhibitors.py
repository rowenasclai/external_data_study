from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("extract_govware_2026_exhibitors.py")
SPEC = importlib.util.spec_from_file_location("extract_govware_2026_exhibitors", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class GovWareParserTests(unittest.TestCase):
    def test_parse_normalizes_and_collapses_exact_repeat_card(self) -> None:
        payload = """
        <a href="javascript:openRemoteModal('exhibitors/example-ltd', 'ajax', {}, false)">
          Example&nbsp;  株式会社
        </a>
        <a href="javascript:openRemoteModal('exhibitors/example-ltd', 'ajax', {}, false)">Example 株式会社</a>
        <a href="javascript:openRemoteModal('exhibitors/second-co', 'ajax', {}, false)">Second Co</a>
        """
        rows, repeats = MODULE.parse_directory(payload)
        self.assertEqual(repeats, 1)
        self.assertEqual([row["exhibitor_id"] for row in rows], ["example-ltd", "second-co"])
        self.assertEqual(rows[0]["company_name"], "Example 株式会社")
        self.assertEqual(rows[0]["source_url"], MODULE.SOURCE_URL)

    def test_conflicting_same_id_is_fail_visible(self) -> None:
        payload = """
        <a href="javascript:openRemoteModal('exhibitors/example', 'ajax', {}, false)">Example</a>
        <a href="javascript:openRemoteModal('exhibitors/example', 'ajax', {}, false)">Different Example</a>
        """
        with self.assertRaisesRegex(ValueError, "conflicting names"):
            MODULE.parse_directory(payload)

    def test_missing_modal_records_is_fail_visible(self) -> None:
        with self.assertRaisesRegex(ValueError, "no named exhibitor"):
            MODULE.parse_directory("<a href='/ordinary'>Ordinary link</a>")

    def test_write_and_read_back_equivalence(self) -> None:
        rows = [{field: "" for field in MODULE.FIELDS}]
        rows[0].update({
            "exhibitor_id": "example",
            "company_name": "例子 Company",
            "source_url": MODULE.SOURCE_URL,
            "source_position": "1",
        })
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path, json_path = root / "out.csv", root / "out.json"
            MODULE.write_outputs(rows, csv_path, json_path)
            self.assertEqual(MODULE.validate_artifacts(csv_path, json_path), 1)


if __name__ == "__main__":
    unittest.main()
