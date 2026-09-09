from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("validate_ifa_berlin_exhibitors.py")
SPEC = importlib.util.spec_from_file_location("validate_ifa_berlin_exhibitors", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class IFAValidationTests(unittest.TestCase):
    def write_pair(self, root: Path, rows: list[dict[str, str]]) -> tuple[Path, Path]:
        csv_path = root / "exhibitors.csv"
        json_path = root / "exhibitors.json"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=MODULE.FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return csv_path, json_path

    def valid_row(self, identifier: str, position: str) -> dict[str, str]:
        row = {field: "" for field in MODULE.FIELDS}
        row.update({
            "exhibitor_id": identifier,
            "company_name": "Example Technology",
            "legal_company_name": "Example Technology GmbH",
            "profile_description": "A plain text company profile.",
            "website_url": "https://example.com/",
            "detail_url": f"https://www.ifa-berlin.com/exhibitors/example-{identifier}",
            "logo_url": "https://www.ifa-berlin.com/logo.png",
            "source_page": "https://www.ifa-berlin.com/exhibitors",
            "source_position": position,
        })
        return row

    def test_valid_equivalent_pair_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            csv_path, json_path = self.write_pair(Path(directory), [self.valid_row("1", "1"), self.valid_row("2", "2")])
            report = MODULE.validate(csv_path, json_path)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["unique_exhibitor_ids"], 2)

    def test_literal_comparison_symbols_in_description_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            row = self.valid_row("1", "1")
            row["profile_description"] = "Capacity is <50 units, and > Petkit is a listed brand."
            csv_path, json_path = self.write_pair(Path(directory), [row])
            report = MODULE.validate(csv_path, json_path)
        self.assertEqual(report["status"], "pass")

    def test_duplicate_ids_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            csv_path, json_path = self.write_pair(Path(directory), [self.valid_row("1", "1"), self.valid_row("1", "2")])
            report = MODULE.validate(csv_path, json_path)
        self.assertEqual(report["status"], "fail")
        self.assertIn("Duplicate exhibitor IDs", report["errors"])

    def test_csv_json_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path, json_path = self.write_pair(root, [self.valid_row("1", "1")])
            changed = [self.valid_row("1", "1")]
            changed[0]["company_name"] = "Different Name"
            json_path.write_text(json.dumps(changed), encoding="utf-8")
            report = MODULE.validate(csv_path, json_path)
        self.assertEqual(report["status"], "fail")
        self.assertIn("CSV and JSON contents differ", report["errors"])


if __name__ == "__main__":
    unittest.main()
