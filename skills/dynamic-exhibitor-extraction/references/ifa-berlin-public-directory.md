# IFA Berlin 2026 public exhibitor-directory contract

**Observed:** 2026-09-07

## Canonical listing

```text
GET https://www.ifa-berlin.com/exhibitors
GET https://www.ifa-berlin.com/exhibitors?page=N
```

- Plain public server-rendered HTML; no login, cookies, or browser automation were needed.
- The title/H1 identifies the directory as **Exhibitors 2026**.
- Pagination is exposed as normal `?page=N` links. The observed last page was `68`; every page should repeat the same maximum page number.
- Listing cards use `.brand-card`; the profile anchor is `.list-item-link` and the stable numeric ID is the associated `button[data-entity-id]`.
- Public card fields: `.name`, `.country`, `.show-area`, `.brand-location-hall`, `.brand-location-stand`, optional image `src`, and profile `href`.
- Some valid cards did not expose a profile URL. Preserve `detail_url` and any profile-only fields as blank rather than rejecting the directory record.

## Public profile enrichment

For rows that have a profile URL, request it at a conservative bounded rate and parse:

- published description: `.description`
- first non-social link under `.social-link-text a[href]` as `website_url`

Do not treat social-media links as the official website; exclude well-known social hostnames. Keep missing description/site values blank. Fail visibly on transport failures after bounded retries instead of producing a partial enriched artifact.

## Completeness and validation

- Traverse pages `1..max_page`, preserve source page order, and require every page to report the same final page number.
- Require nonempty stable IDs and names, then verify IDs are unique.
- Write CSV and JSON from the same normalized records and read both back to prove equality.
- Keep profile enrichment result assignment keyed by the original row index if using concurrency, so completion order cannot alter source order.
