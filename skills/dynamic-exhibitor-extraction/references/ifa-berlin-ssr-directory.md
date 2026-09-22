# IFA Berlin 2026 public exhibitor directory

**Observed:** 2026-09-07

## Canonical source

- Directory: `https://www.ifa-berlin.com/exhibitors`
- The date-suffixed route `/exhibitors-2026` returned 404.
- The canonical route is server-rendered HTML and advertises `Exhibitors 2026`.

## Listing contract

- Pagination is ordinary public HTML: `?page=1` through the maximum page number exposed in pagination links.
- The observed maximum was 68 pages, with 1,902 unique exhibitor cards after sequential traversal.
- Cards expose a `data-entity-id` stable ID, displayed company/brand name, country, show-area chips, hall/stand values, optional logo, and an optional `/exhibitors/<slug>` profile URL.
- There was no authoritative explicit total in the page. Treat complete native-page traversal plus stable-ID uniqueness as the completeness signal; report that limitation.

## Profile enrichment

For nonblank public profile URLs, useful server-rendered fields were:

- Profile description: `div.description`
- Published company/legal name: first `small` inside `div.brand-detail-header-text.gray`
- Company website: first external URL in `div.social-link-text a` that is not a major social network

The profile name is source-published and may equal a brand name for some entries; preserve it as provided and leave it blank when absent. Do not infer legal names from branding.

The examined profiles did not expose named exhibitor contact people. Footer support contacts belong to IFA Management, not the exhibitor, and must not be attributed to exhibitor records.

## Extraction safety

- No login, cookies, CAPTCHA bypass, or browser automation was needed.
- Use bounded concurrency for profile pages, explicit timeouts, retries only for transient failures, deterministic source-order reconstruction, atomic CSV/JSON writes, and read-back equivalence validation.
