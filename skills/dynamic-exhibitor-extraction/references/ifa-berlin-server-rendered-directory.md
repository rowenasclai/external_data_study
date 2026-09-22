# IFA Berlin 2026 public exhibitor directory

Observed 2026-09-07:

- Canonical directory: `https://www.ifa-berlin.com/exhibitors` (not `/exhibitors-2026`, which returned 404).
- The public, server-rendered HTML declares IFA 2026 and contains exhibitor cards directly; no login, cookie, browser rendering, or private endpoint was required.
- Native pages use `?page=N`. The first page exposed links through page 68, yielding 1,902 records in a full sequential extraction.
- Each `div.brand-card` carried a stable public `button[data-entity-id]`, company name (`div.name`), optional country, show-area/hall/stand values, and sometimes a `a.list-item-link` profile URL. Three otherwise valid records lacked a detail URL; preserve it as blank rather than rejecting the record.
- There was no exposed total counter. Completeness basis: discover the terminal page from pagination on page 1, fetch every page 1..terminal, reject missing/empty interior pages or changing terminal-page values, and enforce unique stable IDs.

Use the public HTML contract directly rather than assuming an XHR endpoint. Keep a short inter-page delay and bounded retries.