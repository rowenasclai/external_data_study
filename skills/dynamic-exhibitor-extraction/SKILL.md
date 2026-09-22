---
name: dynamic-exhibitor-extraction
description: Extract and verify dynamic exhibitor directories.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Data Extraction, Exhibitors, Web APIs, Validation, Git]
---

# Dynamic Exhibitor Extraction

Build a reproducible extractor for a dynamic exhibitor directory by discovering and following the site's public data contract. This workflow does not bypass authentication, anti-bot controls, access restrictions, or site terms, and it does not treat OCR from a static floorplan as equivalent to a complete public directory API.

## When to Use

- A user asks to extract a complete exhibitor list from a JavaScript-driven page.
- Browser-visible cards are absent or incomplete in the initial HTML.
- The site exposes embedded application JSON, an XHR/fetch endpoint, or an iframe application.
- The result must include tested parser code, equivalent CSV/JSON, completeness checks, and a safely integrated Git commit.
- Do not use this workflow to defeat login, CAPTCHA, signed-request expiry, private APIs, or access controls.

## Prerequisites

- A repository checkout and the canonical exhibitor landing-page URL.
- Python 3 in the repository's existing environment; install dependencies only in its declared virtual environment.
- Hermes tools: `read_file`, `search_files`, `web_extract`, `browser_navigate`, `browser_snapshot`, `terminal`, `write_file`, and `patch` as available.
- Network access with normal TLS verification. Never use insecure TLS flags or disabled certificate checks.
- Push access only if the user requested publication. Never inspect, print, copy, or embed credential values.

## How to Run

Use Hermes file and web tools for inspection. Invoke repository commands, tests, artifact checks, and Git through the `terminal` tool with the repository as its working directory.

Canonical implementation shape:

```text
python <extractor>.py --output <result>.csv --json-output <result>.json
python -m unittest <parser-test-module>
```

Use the repository's existing test runner instead when one is documented.

## Quick Reference

```text
Landing page       -> initial HTML, scripts, iframe, embedded JSON
Browser rendering  -> DOM plus public XHR/fetch behavior
Public endpoint    -> method, parameters, headers, cookies, response schema
Pagination         -> native page size, index/cursor, reported total
Identity           -> stable endpoint ID, not row position or display name
CSV encoding       -> UTF-8 with BOM when matching spreadsheet-friendly peers
JSON encoding      -> UTF-8, ensure_ascii=false, trailing newline
Completeness       -> extracted count == reported total; IDs are unique
Integration        -> focused commit, fetch, rebase, ancestry check, push
```

## Procedure

1. Establish repository and worktree safety.

   - Read repository instructions and analogous `ai_extract_*_exhibitors.py` files before designing the extractor.
   - Through `terminal`, capture:

     ```bash
     git status --short --branch
     git log -5 --oneline --decorate
     git remote -v
     ```

   - Treat every pre-existing modification and untracked file as unrelated unless the user identified it as part of the task. Do not reset, clean, overwrite, stage, or silently stash unrelated work.
   - If the checkout is dirty, prefer a separate Git worktree based on the intended upstream branch. If continuing in place is necessary, stage only explicit task paths and inspect the staged diff before committing.
   - Completion criterion: the base branch, upstream, pre-existing work, and task-owned paths are known.

2. Inspect the landing page before automating a browser.

   - Fetch the canonical page with `web_extract` or a small `requests.Session` probe through `terminal`, preserving normal TLS verification.
   - Look for server-rendered records, `<script type="application/json">` state, hydration/warmup JSON, iframe sources, script URLs, pagination labels, totals, and stable detail-page identifiers. For Next.js, specifically parse `script#__NEXT_DATA__`; it may contain the complete public page payload even when a presumed XHR is unavailable.
   - Treat a successful canonical HTML page with embedded structured records as a public data contract in its own right. Do not infer an API endpoint from frontend routes or build artifacts; if a candidate XHR/data route is blocked or cannot be observed, report it as unproven and use the public HTML contract if it is sufficient.
   - Use `search_files` and `read_file` for saved HTML or JavaScript. Do not use shell text-search utilities when Hermes wrappers are available.
   - Use `browser_navigate` and `browser_snapshot` only when initial HTML is insufficient. Observe the page's own public fetch/XHR behavior and loaded iframe, rather than scraping rendered cards one scroll at a time.
   - Do not preserve session-specific signed URLs, tokens, cookies, or personal request headers in code, tests, notes, or the skill.
   - Completion criterion: records are classified as server HTML, embedded JSON, public endpoint data, or static-media-only evidence.

3. Prove the public data contract with a minimal probe.

   - Reproduce one first-page request using only fields demonstrated by the page or its public scripts: HTTP method, endpoint path, query/form/JSON parameters, native page size, page index or cursor, required origin/referer, and landing-page cookies when genuinely required.
   - Send a clear user agent and bounded timeout. Keep TLS verification enabled.
   - Remove incidental browser headers one at a time so the final extractor carries only necessary public request context.
   - Parse the response enough to identify records, a stable ID, and any endpoint-reported total. Fail visibly on missing separators, malformed JSON, schema drift, missing totals when completeness depends on them, or a nonzero total with zero rows.
   - If the request needs private credentials, rotating signatures, CAPTCHA solving, or bypass behavior, stop and report the limitation.
   - Completion criterion: a repeatable, non-secret first-page request returns parseable public records and its completeness signal.

4. Follow native pagination exactly.

   - Use the site's own page size. Do not replace native pagination with an oversized page merely because the endpoint appears to accept it.
   - Fetch page 1 first, derive page count from the reported total, and request every remaining native page or follow every cursor until the endpoint's terminal condition.
   - Preserve source order by collecting pages under their page index and flattening in index order, regardless of request completion order.
   - Start sequentially. Increase to only a small worker count after the endpoint is stable; keep concurrency bounded and configurable.
   - Require each page to report the same total as page 1 when totals are repeated. Reject missing pages and unexpected empty interior pages.
   - Assign `source_position` only after deterministic ordering; never use it as record identity.
   - Completion criterion: every native page/cursor is accounted for exactly once and ordering is deterministic.

5. Retry conservatively.

   - Set explicit connect/read or per-request timeouts and a small configurable retry count.
   - Retry only transient transport failures and transient HTTP responses such as timeout, connection reset, 408, 429, and 5xx. Honor `Retry-After` when present.
   - Use capped exponential backoff with no busy loop. Keep concurrency low during retries.
   - Do not retry deterministic parser/schema errors indefinitely, ordinary 4xx authorization failures, CAPTCHA pages, or a request contract known to be invalid.
   - Include page/cursor and attempt count in errors, but never log cookies, authorization headers, signed URLs, or response content that may contain secrets.
   - Completion criterion: retries are bounded, rate-aware, and failures remain auditable.

6. Separate transport, parsing, normalization, validation, and writing.

   - Keep a pure parser that accepts response text or decoded JSON and returns normalized rows plus endpoint metadata. It must be unit-testable without network access.
   - Normalize visible whitespace without transliterating or discarding multilingual text. Resolve relative detail/logo links against the canonical public source page.
   - Prefer an immutable endpoint ID. If no stable ID exists, document and test the chosen compound key; do not silently deduplicate by company name.
   - Require non-empty company names and any other fields essential to the requested contract.
   - Keep source URL and source position as provenance fields where appropriate.
   - Completion criterion: fixture parsing is deterministic and validation is independent from live networking.

7. Verify totals and identities before writing.

   - Require `len(rows) == reported_total` when the endpoint reports a total.
   - Require exactly one row per stable ID and report a bounded sample of duplicate IDs without quadratic counting.
   - Require all fetched pages to agree on totals and reject missing page indexes.
   - If the endpoint has no total, use documented terminal pagination plus a second independent signal when available, such as the UI count or embedded metadata. Label any remaining completeness uncertainty explicitly.
   - Never claim API-level completeness from a manually transcribed floorplan. For static-media-only sources, preserve source provenance and per-row OCR uncertainty in a distinct workflow.
   - Completion criterion: completeness and identity invariants pass before either artifact is created.

8. Produce equivalent UTF-8 CSV and JSON atomically.

   - Write both outputs from the same validated ordered row list and the same field order.
   - Match repository convention; for spreadsheet-compatible peers use `utf-8-sig` CSV with `newline=""`, a header, and `\n` line endings. Use UTF-8 JSON with `ensure_ascii=False`, deterministic indentation, and a final newline.
   - Create parent directories deliberately. Write temporary files in the destination directory, flush them, then atomically replace final paths so failure cannot leave a plausible partial artifact.
   - Do not include credentials, cookies, transient request URLs, or unrelated response fields in output.
   - Completion criterion: both final paths exist only after successful validation and writing.

9. Test parsers and failure behavior.

   - Add sanitized, minimal fixtures containing invented records rather than generated exhibitor data.
   - Test a valid response, multilingual/whitespace preservation, relative URL resolution, and endpoint total parsing.
   - Test fail-visible cases: missing response separator or key, malformed payload, count mismatch, duplicate IDs, missing required name, inconsistent totals, and missing page.
   - Mock transport for retry tests; unit tests must not depend on the live site.
   - Run the focused parser tests, then the repository's broader relevant suite.
   - Completion criterion: success and invariant failures are covered by deterministic offline tests.

10. Validate generated artifacts by reading them back.

    - Parse CSV with `encoding="utf-8-sig"` and JSON with `encoding="utf-8"`.
    - Assert equal row counts, equal field sets and order, equal stable-ID sequences, and field-for-field equivalence after CSV scalar normalization.
    - Re-run uniqueness, required-field, and total checks against both loaded artifacts.
    - Confirm JSON preserves non-ASCII text and neither artifact contains accidental HTML error pages.
    - Review a small beginning/middle/end sample for ordering and normalization without copying records into durable skill documentation.
    - Completion criterion: independent read-back proves CSV and JSON represent the same validated dataset.

11. Review, scan, and commit only task files.

    - Run syntax checks, focused tests, artifact validation, and:

      ```bash
      git diff --check
      git status --short
      git diff -- <task-paths>
      ```

    - Stage explicit paths, never `git add .` in a checkout containing unrelated work. Inspect:

      ```bash
      git diff --cached --check
      git diff --cached --stat
      git diff --cached
      ```

    - Secret-scan the staged patch and task files with the repository's documented scanner. If none exists, inspect the staged patch for private-key blocks, authorization/cookie assignments, common token prefixes, signed-query parameters, and high-entropy credential material. Do not print matched secret values; remove and rotate real exposures.
    - Commit one focused change only after every staged path is accounted for. Confirm unrelated work remains untouched.
    - Completion criterion: the focused commit contains code, tests, and requested artifacts only, with no secret-bearing material.

12. Rebase and fast-forward publish safely.

    - Fetch without rewriting local work:

      ```bash
      git fetch origin
      git rebase origin/main
      ```

    - Re-run tests, artifact validation, `git diff --check`, and the secret scan after the rebase. On conflict, inspect each file and resolve intentionally; never use blanket ours/theirs selection. Abort the rebase if provenance is unclear.
    - Before updating the shared branch, prove ancestry:

      ```bash
      git merge-base --is-ancestor origin/main HEAD
      git status --short --branch
      ```

    - Require a clean task worktree and a zero exit status from the ancestry check. Then use the repository's normal non-force push, for example `git push origin HEAD:main`. Never force-push a shared branch for this workflow.
    - If the remote advances, fetch and rebase again; do not bypass the rejection. Fetch after pushing and verify the published remote contains the intended commit.
    - Completion criterion: push succeeds as a non-force fast-forward, the remote contains the tested commit, and unrelated local work is still present and unmodified.

## Reference

- `references/hktdc-nextjs-ssr-directory.md` — observed example of a public HKTDC directory whose complete paginated payload was embedded in Next.js SSR HTML; use it as a probing pattern, not as a permanent contract.
- `references/ifa-berlin-server-rendered-directory.md` — public static-HTML directory example with pagination but no reported total; use terminal-page coverage plus stable-ID validation.
- `references/ifa-berlin-public-directory.md` — observed IFA Berlin 2026 listing and optional public profile-enrichment contract; use it as a probing pattern, not as a permanent contract.
- `references/ifa-berlin-ssr-directory.md` — IFA-specific field mapping for public profile descriptions, source-published company/legal names, websites, and the requirement not to misattribute organizer-footer contact information.

## Pitfalls

- Scraping rendered cards misses lazy-loaded pages and hides the authoritative total; discover the page's public contract first.
- Increasing `pageSize` can produce silent truncation, changed ordering, or server stress; honor native pagination.
- Concurrent futures complete out of order; store by page index before flattening.
- A row count can match while duplicates hide omissions; require both total equality and unique stable IDs.
- Retrying parser failures can hammer a changed endpoint; distinguish transient transport from deterministic schema errors.
- CSV and JSON written by separate transformations drift; serialize both from one normalized list and compare read-backs.
- Embedded frontend constants are not automatically credentials, but do not reproduce obfuscation or access-control mechanisms without authorization.
- `git status` being clean after a careless reset is not preservation. Record initial state and avoid destructive Git commands.
- A successful push does not prove the intended remote branch contains the commit; fetch and verify.

## Verification

The workflow is complete only when one verification run proves all of the following: offline parser tests pass; the live extraction traverses native pagination; extracted count matches the endpoint total; stable IDs are unique; CSV and JSON read back as field-for-field equivalent UTF-8 datasets; syntax, diff, and secret checks pass; the focused commit rebases cleanly; and any requested push is verified as a non-force fast-forward without altering unrelated work.
