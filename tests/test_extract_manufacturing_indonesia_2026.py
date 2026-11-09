import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "PY/Exhibit exploration/extract_manufacturing_indonesia_2026.py"
spec = importlib.util.spec_from_file_location("manufacturing_indonesia", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load {MODULE_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ManufacturingIndonesiaParserTests(unittest.TestCase):
    def payload(self, records, total=None):
        total = len(records) if total is None else total
        return {"recordsTotal": total, "recordsFiltered": total, "data": records}

    def record(self, exhibitor_id="42", name="  星  Test  Co.  "):
        return {
            "ExhibitorID": exhibitor_id,
            "ExhibitorNameEn": name,
            "CountryEn": "  Indonesia ",
            "StandNoStr": " Hall A  ",
        }

    def test_valid_page_normalizes_visible_whitespace_and_builds_url(self):
        rows, total = module.parse_page(self.payload([self.record()]))
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["company_name"], "星 Test Co.")
        self.assertEqual(rows[0]["detail_url"], module.LANDING_URL + "/exhibitor/42/星-test-co-")
        self.assertEqual(rows[0]["country"], "Indonesia")

    def test_missing_required_name_fails(self):
        with self.assertRaisesRegex(ValueError, "company name"):
            module.parse_page(self.payload([self.record(name=" ")]))

    def test_missing_total_fails(self):
        with self.assertRaisesRegex(ValueError, "missing API key"):
            module.parse_page({"recordsFiltered": 0, "data": []})

    def test_inconsistent_total_fails(self):
        with self.assertRaisesRegex(ValueError, "inconsistent total"):
            module.parse_page(self.payload([self.record()], total=2), expected_total=1)

    def test_validation_rejects_count_mismatch_and_duplicate_ids(self):
        rows, _ = module.parse_page(self.payload([self.record("42"), self.record("42", "Other")]))
        with self.assertRaisesRegex(ValueError, "row count"):
            module.validate_rows(rows, 3, 1)
        with self.assertRaisesRegex(ValueError, "duplicate stable IDs"):
            module.validate_rows(rows, 2, 1)

    def test_validation_rejects_missing_page_count(self):
        records = [self.record(str(index), f"Company {index}") for index in range(25)]
        rows, _ = module.parse_page(self.payload(records))
        with self.assertRaisesRegex(ValueError, "missing or unexpected pages"):
            module.validate_rows(rows, 25, 1)


if __name__ == "__main__":
    unittest.main()
