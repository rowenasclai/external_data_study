import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


control = load_module("hktdc_control-hermes.py", "hktdc_control_hermes")
extractor = load_module("hktdc_exhibit-hermes.py", "hktdc_exhibit_hermes")


class ControlSelectionTests(unittest.TestCase):
    def test_selects_only_nonblank_prefixes_at_supported_offsets(self):
        rows = [
            {"prefix": "alpha", "event_start_date": "8/13/26 0:00"},
            {"prefix": "", "event_start_date": "8/13/26 0:00"},
            {"prefix": "later", "event_start_date": "8/14/26 0:00"},
        ]
        selected = control.select_events(rows, date(2026, 7, 14))
        self.assertEqual([row["prefix"] for row in selected], ["alpha"])

    def test_rejects_invalid_prefix(self):
        with self.assertRaises(ValueError):
            control.select_events([{"prefix": "not valid", "event_start_date": "8/13/26 0:00"}], date(2026, 7, 14))


class ExtractorTests(unittest.TestCase):
    def test_normalize_and_write_readback(self):
        row = extractor.normalize(
            {"id": "stable-1", "exhibitorName": "  Example  Company ", "countryDesc": "Hong   Kong", "boothNumbers": ["A01"], "exhibitorUrn": "urn:example"},
            1,
            "https://example.test/page",
        )
        self.assertEqual(row["exhibitor_name"], "Example Company")
        self.assertEqual(row["booth_numbers"], '["A01"]')
        original_root = extractor.OUTPUT_ROOT
        with tempfile.TemporaryDirectory() as directory:
            extractor.OUTPUT_ROOT = Path(directory)
            json_path, csv_path = extractor.write_outputs("example", [row])
            self.assertTrue(json_path.is_file())
            self.assertTrue(csv_path.is_file())
        extractor.OUTPUT_ROOT = original_root

    def test_missing_required_values_fail(self):
        with self.assertRaises(ValueError):
            extractor.normalize({"exhibitorName": "Example"}, 1, "https://example.test")
        with self.assertRaises(ValueError):
            extractor.normalize({"id": "stable-1"}, 1, "https://example.test")


if __name__ == "__main__":
    unittest.main()
