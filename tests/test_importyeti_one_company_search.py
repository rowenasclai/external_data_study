import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "importyeti_one_company_search.py"
SPEC = importlib.util.spec_from_file_location("importyeti_one_company_search", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OneCompanySearchHelperTests(unittest.TestCase):
    def test_legal_suffix_and_distinctive_terms(self):
        self.assertEqual(MODULE.core_tokens("North Star Mfg. Ltd."), ("north", "star", "mfg"))
        self.assertEqual(MODULE.name_score("Alpha Components Ltd.", "Alpha Components Inc."), 1.0)

    def test_single_token_exact_candidate_allowed_but_not_fuzzy(self):
        candidates = [
            {"name": "Ceylon Pvt Ltd", "url": "https://www.importyeti.com/company/ceylon"},
            {"name": "Ceylon Industries", "url": "https://www.importyeti.com/company/ceylon-industries"},
        ]
        ranked = MODULE.rank_candidates("Ceylon Pvt. Ltd.", candidates)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["name"], "Ceylon Pvt Ltd")
        self.assertEqual(ranked[0]["similarity"], 1.0)

    def test_access_gate_detection_and_url_sanitizing(self):
        self.assertTrue(MODULE.is_access_gate("https://www.importyeti.com/register?limitReached=1", ""))
        self.assertTrue(MODULE.is_access_gate("https://www.importyeti.com/search", "Login is required"))
        self.assertFalse(MODULE.is_access_gate("https://www.importyeti.com/search", "Search results"))
        self.assertEqual(
            MODULE.safe_url("https://www.importyeti.com/company/example?tracking=demo#frag"),
            "https://www.importyeti.com/company/example",
        )


if __name__ == "__main__":
    unittest.main()
