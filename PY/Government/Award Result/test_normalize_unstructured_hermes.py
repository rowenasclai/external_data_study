import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("GOV_HERMES_DATA_DIR", tempfile.mkdtemp())
MODULE_PATH = Path(__file__).with_name("normalize_unstructured_hermes.py")
spec = importlib.util.spec_from_file_location("normalize_unstructured_hermes", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class NormalizeHermesTests(unittest.TestCase):
    def test_hkaa_contract_paragraph(self):
        raw = {
            "ref": "E3002",
            "publish_date": "2026-07-13",
            "description": "Bus Terminus at SkyPier Terminal",
            "type": "Notice of Contract Award",
            "url": "https://example.invalid/e3002",
            "extracted_content": (
                '[{"paragraph 1":"Notice is hereby given that the Airport Authority awarded '
                'Contract E3002 for Bus Terminus at SkyPier Terminal to China Harbour Engineering '
                'Company Limited of 19/F, China Harbour Building, North Point, Hong Kong on '
                '13 July 2026. The awarded contract sum was HK$75,924,123."}]'
            ),
            "markdown": "",
        }
        record, error = module.normalize_hkaa(raw)
        self.assertIsNone(error)
        self.assertEqual(record["awardee"], "China Harbour Engineering Company Limited")
        self.assertEqual(record["award_date"], "2026-07-13")
        self.assertEqual(record["sum"], "HK$75,924,123")

    def test_gld_structured_cells(self):
        raw = {
            "ref": "A123",
            "department": "Department A",
            "particulars": "Supply service",
            "Contractor(s) & Address(es)": "Example Services Limited\n1 Test Road, Hong Kong",
            "Amount / Contract Award Date": "HK$1,234,567\n13 Jul 2026",
        }
        record, error = module.normalize_gld(raw)
        self.assertIsNone(error)
        self.assertEqual(record["awardee"], "Example Services Limited")
        self.assertEqual(record["award_date"], "13 Jul 2026")
        self.assertEqual(record["sum"], "HK$1,234,567")

    def test_unmatched_hkaa_is_rejected(self):
        record, error = module.normalize_hkaa({"extracted_content": "no contract evidence"})
        self.assertIsNone(record)
        self.assertIn("missing", error)


if __name__ == "__main__":
    unittest.main()
