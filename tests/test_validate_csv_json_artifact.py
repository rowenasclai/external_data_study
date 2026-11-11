from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_csv_json_artifact import load_csv, read_back, validate, write_json


class CsvJsonArtifactTests(unittest.TestCase):
    def make_csv(self, directory: Path, rows: list[dict[str, str]]) -> Path:
        path = directory / "source.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "name", "detail_page_url"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_round_trip_preserves_fields_and_non_ascii(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = self.make_csv(root, [{"id": "one", "name": "测试公司", "detail_page_url": "https://example.test/one"}])
            fields, rows = load_csv(csv_path)
            validate(fields, rows, "id", "name", 1)
            json_path = root / "result.json"
            write_json(json_path, fields, rows, csv_path, 1)
            read_back(csv_path, json_path)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["records"][0]["name"], "测试公司")

    def test_rejects_duplicate_ids_and_count_drift(self) -> None:
        fields = ["id", "name", "detail_page_url"]
        rows = [{"id": "same", "name": "One", "detail_page_url": "https://example.test/1"}, {"id": "same", "name": "Two", "detail_page_url": "https://example.test/2"}]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate(fields, rows, "id", "name", 2)
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            validate(fields, rows[:1], "id", "name", 2)


if __name__ == "__main__":
    unittest.main()
