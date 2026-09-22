from __future__ import annotations

import unittest

from scripts.extract_ceatec_2026_exhibitors import parse_listing, validate


FIXTURE = '''
<span class="exl-header__total-num">3</span> companies in total
<article class="exl-card" data-exl-card data-id="42">
<h3 class="exl-card__name"> 株式会社 &amp; Co. </h3>
<span class="exl-card__area">● Future Zone</span><span class="exl-card__hall">Hall 1</span><span class="exl-card__booth">A01</span>
<button type="button" class="exl-child"> 子会社 One </button>
<button type="button" class="exl-child">Child &amp; Two</button>
</article>'''


class CeatecParserTests(unittest.TestCase):
    def test_parent_and_coexhibitors_are_complete_and_deterministic(self) -> None:
        rows, total, parents = parse_listing(FIXTURE)
        self.assertEqual((len(rows), total, parents), (3, 3, 1))
        self.assertEqual(rows[0]["company_name"], "株式会社 & Co.")
        self.assertEqual(rows[1]["exhibitor_id"], "parent:42:co-exhibitor:1")
        self.assertEqual(rows[2]["company_name"], "Child & Two")
        self.assertEqual(rows[2]["booth"], "A01")
        validate(rows, total)

    def test_missing_total_fails_visibly(self) -> None:
        with self.assertRaisesRegex(ValueError, "reported total"):
            parse_listing(FIXTURE.replace('class="exl-header__total-num"', 'class="removed"'))

    def test_count_mismatch_and_duplicate_ids_fail(self) -> None:
        rows, total, _ = parse_listing(FIXTURE)
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            validate(rows, total + 1)
        rows[1]["exhibitor_id"] = rows[0]["exhibitor_id"]
        with self.assertRaisesRegex(ValueError, "duplicate stable IDs"):
            validate(rows, total)

    def test_missing_company_name_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty source ID or name"):
            parse_listing(FIXTURE.replace('株式会社 &amp; Co.', '   '))


if __name__ == "__main__":
    unittest.main()
