# HKTDC Next.js SSR directory probe (observed 2026-09-07)

Canonical public page examined:

```text
https://www.hktdc.com/event/hkelectronicsfairae/en/exhibitor-list?pageNum=1&pageSize=50
```

A normal unauthenticated `GET` returned HTML with a Next.js `__NEXT_DATA__` JSON script. The public directory payload was at:

```python
json.loads(next_data)["props"]["pageProps"]["exhibitorListData"]
```

Observed paging keys: `from`, `size`, `totalSize`, `data`. `data` was a list of exhibitor rows. At the time of the probe, `pageNum=1&pageSize=50` reported `from=0`, `size=50`, `totalSize=1365`, and 50 records; page 28 returned 15 records (`from=1350`). Omitting `pageSize` resulted in `size=10`.

Rows exposed `id`, `exhibitorUrn`, `supplierUrn`, and `ccdid`; prefer the opaque `id` as the candidate record identity after validating uniqueness.

Do not call an internal API merely because the frontend is Next.js. In this case, ordinary Next `_next/data` and direct static-chunk requests received 403, while the canonical public page was sufficient. Report that a separate XHR endpoint was not proven rather than treating a guessed route or restricted response as an API contract. Do not bypass those restrictions.

## Scheduled control integration

For a daily pre-event runner, keep the source-control CSV as the default and select only safe nonblank `prefix` values whose parsed `event_start_date` is an explicitly requested lead-time date. A future Google Sheets source should be a public, read-only CSV export fetched at run time; never persist Google credentials or session data. Keep generated outputs in a separate result subtree, stage only that subtree in the scheduled job, run tests and artifact validation before committing, and use fetch/rebase/non-force-push/remote-SHA verification for each publication.
