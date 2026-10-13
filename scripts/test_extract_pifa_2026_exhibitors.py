from __future__ import annotations

import unittest

from scripts.extract_pifa_2026_exhibitors import parse_listing, validate


FIXTURE = '''
<div class="js-librarylistwrapper" data-totalcount="2">
<article class="m-exhibitors-list__list__items__item m-exhibitors-list__list__items__item--id-101">
  <h2 class="m-exhibitors-list__list__items__item__header__title"> 株式会社 &amp; Co. </h2>
  <span class="m-exhibitors-list__list__items__item__header__meta__stand"> Stand: A01 </span>
  <a href="javascript:openRemoteModal('exhibitors/example-one','ajax',{},false,'',{});">profile</a>
</article>
<article class="m-exhibitors-list__list__items__item m-exhibitors-list__list__items__item--id-102">
  <h2> Example Two </h2>
  <a href="javascript:openRemoteModal('exhibitors/example-two','ajax',{},false,'',{});">profile</a>
</article>
</div>'''


class PifaParserTests(unittest.TestCase):
    def test_valid_listing_preserves_unicode_and_relative_profile_route(self) -> None:
        rows, total = parse_listing(FIXTURE)
        self.assertEqual(total, 2)
        self.assertEqual(rows[0]["company_name"], "株式会社 & Co.")
        self.assertEqual(rows[0]["stand"], "A01")
        self.assertEqual(rows[0]["profile_url"], "https://www.prointegrationfuture.asia/exhibitors/example-one")
        self.assertEqual([row["source_position"] for row in rows], ["1", "2"])
        validate(rows, total)

    def test_missing_total_or_profile_route_fails_visibly(self) -> None:
        with self.assertRaisesRegex(ValueError, "reported total"):
            parse_listing(FIXTURE.replace('data-totalcount', 'data-removed'))
        with self.assertRaisesRegex(ValueError, "profile route"):
            parse_listing(FIXTURE.replace("exhibitors/example-one", ""))

    def test_count_mismatch_duplicate_id_and_missing_name_fail(self) -> None:
        rows, total = parse_listing(FIXTURE)
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            validate(rows, total + 1)
        rows[1]["exhibitor_id"] = rows[0]["exhibitor_id"]
        with self.assertRaisesRegex(ValueError, "duplicate stable IDs"):
            validate(rows, total)
        with self.assertRaisesRegex(ValueError, "empty name"):
            parse_listing(FIXTURE.replace("Example Two", "   "))


if __name__ == "__main__":
    unittest.main()
