#!/usr/bin/env python3
"""One-shot, headed Playwright search using ImportYeti's visible UI.

Usage::

    python scripts/importyeti_one_company_search.py "Example Company Ltd"

This sends at most one visible search-form submission. It does not use hidden
endpoints, stored cookies, proxies, stealth settings, login automation, retries,
or CAPTCHA handling. It stops on a 403/429 or visible login/limit gate.
Search-result names are candidate suggestions only, not identity confirmation.
Playwright and its Chromium browser must be installed in the chosen Python environment.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit

HOME_URL = "https://www.importyeti.com/"
SEARCH_PLACEHOLDER = "Find Any Company's Suppliers"
LEGAL_SUFFIXES = {
    "co", "company", "corp", "corporation", "inc", "incorporated",
    "ltd", "limited", "llc", "pte", "private", "pvt", "plc", "pty",
    "gmbh", "bv", "sdn", "bhd",
}
GATE_TEXT = (
    "limit reached",
    "login is required",
    "log in is required",
    "sign in to continue",
    "please log in",
    "please sign in",
)


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch if ch.isalnum() else " " for ch in normalized).split()


def core_tokens(text: str) -> tuple[str, ...]:
    result = tokens(text)
    while result and result[-1] in LEGAL_SUFFIXES:
        result.pop()
    return tuple(result)


def name_score(query: str, candidate: str) -> float:
    left, right = core_tokens(query), core_tokens(candidate)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    # Avoid fuzzy matches based on a single generic distinguishing token.
    if len(left) < 2 or len(right) < 2:
        return 0.0
    a, b = set(left), set(right)
    jaccard = len(a & b) / len(a | b)
    sequence = SequenceMatcher(None, " ".join(left), " ".join(right)).ratio()
    return 0.6 * jaccard + 0.4 * sequence


def rank_candidates(query: str, candidates: list[dict[str, str]], minimum_score: float = 0.45) -> list[dict[str, str | float]]:
    ranked: list[dict[str, str | float]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        name = (candidate.get("name") or "").strip()
        url = (candidate.get("url") or "").strip()
        if not name:
            continue
        key = (name.casefold(), url)
        if key in seen:
            continue
        seen.add(key)
        score = name_score(query, name)
        if score >= minimum_score:
            ranked.append({"name": name, "url": url, "similarity": round(score, 4)})
    ranked.sort(key=lambda item: (-float(item["similarity"]), str(item["name"]).casefold(), str(item["url"])))
    return ranked[:5]


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    # Do not persist query parameters or fragments that could contain transient state.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def is_access_gate(url: str, body: str) -> bool:
    path = urlsplit(url).path.casefold()
    body_lower = body.casefold()
    return (
        "limitreached" in url.casefold()
        or path.startswith("/register")
        or any(term in body_lower for term in GATE_TEXT)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit one company search in the visible ImportYeti UI and rank visible linked names."
    )
    parser.add_argument("company", help="One company name to search")
    parser.add_argument("--minimum-score", type=float, default=0.45,
                        help="Candidate display threshold from 0 to 1; candidates remain unverified")
    parser.add_argument("--pause", action="store_true",
                        help="Keep the visible browser open until Enter is pressed")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    query = args.company.strip()
    if not query:
        print("ERROR: company name must not be empty", file=sys.stderr)
        return 2
    if not 0.0 <= args.minimum_score <= 1.0:
        print("ERROR: --minimum-score must be between 0 and 1", file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright is not installed in this Python environment", file=sys.stderr)
        return 2

    responses: list[tuple[int, str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(20_000)
        page.on(
            "response",
            lambda response: responses.append((response.status, safe_url(response.url)))
            if response.request.resource_type in {"document", "xhr", "fetch"}
            else None,
        )
        exit_code = 0
        try:
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=45_000)
            body = page.locator("body").inner_text(timeout=10_000)
            if any(status in (403, 429) for status, _ in responses) or is_access_gate(page.url, body):
                print(f"ACCESS GATE: stop without retrying. Page: {safe_url(page.url)}")
                print("No search was submitted; sign-in/limit gates are not automated by this script.")
                return 3

            search = page.get_by_placeholder(SEARCH_PLACEHOLDER)
            try:
                search.wait_for(state="visible", timeout=20_000)
            except PlaywrightTimeoutError:
                print(f"Search form not visible. Page: {safe_url(page.url)}")
                print("No search was submitted; inspect the visible page manually.")
                return 4

            search.click()
            search.press_sequentially(query, delay=60)
            entered = search.input_value()
            if entered.strip() != query:
                print("Search input did not retain the complete query; stopped without submitting.")
                return 4

            button = page.get_by_role("button", name="Search button")
            button.click()  # exactly one visible submission
            page.wait_for_timeout(7000)

            body = page.locator("body").inner_text(timeout=10_000)
            if any(status in (403, 429) for status, _ in responses) or is_access_gate(page.url, body):
                blocked = next(((status, url) for status, url in responses if status in (403, 429)), None)
                detail = f" HTTP {blocked[0]} at {blocked[1]}." if blocked else ""
                print(f"ACCESS GATE: stop without retrying.{detail} Page: {safe_url(page.url)}")
                print("No result was treated as a match; use the site manually or an authorized export.")
                return 3

            anchors = page.locator("a:visible").evaluate_all(
                "els => els.map(a => ({name: (a.innerText || '').trim(), url: a.href}))"
            )
            visible: list[dict[str, str]] = []
            for anchor in anchors:
                name = " ".join((anchor.get("name") or "").split())
                url = safe_url(anchor.get("url") or "")
                if not name or not url:
                    continue
                if urlsplit(url).hostname not in {"importyeti.com", "www.importyeti.com"}:
                    continue
                visible.append({"name": name, "url": url})

            ranked = rank_candidates(query, visible, args.minimum_score)
            print(f"Search submitted once for: {query}")
            print(f"Result page: {safe_url(page.url)}")
            if not ranked:
                print("No visible linked names met the candidate threshold; this is not proof of no result.")
            else:
                print("Visible linked-name candidates (heuristic only; verify name, location, and profile manually):")
                for index, candidate in enumerate(ranked, start=1):
                    print(f"{index}. {candidate['name']} | score={candidate['similarity']:.4f} | {candidate['url']}")
            print("No profile pages were opened and no shipment figures were extracted.")
            if args.pause and sys.stdin.isatty():
                input("Press Enter to close the browser…")
        except PlaywrightTimeoutError as exc:
            print(f"TIMEOUT: {exc}; stopped without retrying.", file=sys.stderr)
            exit_code = 5
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            exit_code = 1
        finally:
            context.close()
            browser.close()
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
