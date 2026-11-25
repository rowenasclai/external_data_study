"""
Enrich aie_expo_exhibitors_en.csv with Booth, Category, Location, Website,
Featured Products, and Company Profile from the AIE Online Exhibitor Directory.

Usage:
    python3 fetch_aie_exhibitor_details.py

Requirements:
    Python 3.8+ (standard library only; place aie_expo_exhibitors_en.csv in the same folder).
"""

import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

os.chdir('/Users/rowena/Downloads')
INPUT_CSV = "aie_expo_exhibitors_en.csv"
OUTPUT_CSV = "aie_expo_exhibitors_en_details.csv"
DETAIL_API = "https://admin.aie-expo.com/aie-admin-api/portal/getExhiInfoAndBoothNumById"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

HTML_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: str) -> str:
    if not value:
        return ""
    text = html.unescape(str(value))
    text = HTML_TAG_RE.sub(" ", text)
    text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln).strip()


def fetch_detail(row: dict) -> tuple[dict, dict | None, str | None]:
    url = row["URL"].strip()
    exhi_id = url.rstrip("/").split("/")[-1]
    zone = row.get("Zone", "")
    expo_id = 1588 if "Zhuhai" in zone else 1604

    query = urllib.parse.urlencode({
        "exhiId": exhi_id,
        "expoId": expo_id,
        "pageNo": 1,
        "pageSize": 100,
    })
    api_url = f"{DETAIL_API}?{query}"

    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(api_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("code") == 200 and payload.get("data"):
                time.sleep(0.05)
                return row, payload["data"], None
            last_err = f"code={payload.get('code')} msg={payload.get('msg')}"
        except Exception as exc:
            last_err = str(exc)
        time.sleep(0.5 * (attempt + 1))

    return row, None, last_err


def main() -> None:
    with open(INPUT_CSV, "r", encoding="utf-8-sig", newline="") as f:
        input_rows = list(csv.DictReader(f))

    print(f"Loaded {len(input_rows)} rows from {INPUT_CSV}")
    results: dict[str, dict | None] = {}
    errors: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_detail, r) for r in input_rows]
        for idx, fut in enumerate(as_completed(futures), start=1):
            row, data, err = fut.result()
            results[row["URL"]] = data
            if err:
                errors.append((row["URL"], err))
            if idx % 100 == 0 or idx == len(input_rows):
                print(f"Progress: {idx}/{len(input_rows)} (errors: {len(errors)})")

    fieldnames = [
        "URL",
        "Exhibitor Name (English)",
        "Booth",
        "Zone",
        "Category",
        "Location",
        "Website",
        "Featured Products",
        "Company Profile",
    ]

    output_rows = []
    for row in input_rows:
        data = results.get(row["URL"]) or {}
        ec = data.get("exhiCorp") or {}
        products_list = (data.get("pageInfo") or {}).get("list") or []

        # Combine booth values without duplicates
        booth_tokens = []
        raw_booths = [row.get("Booth", "")]
        for key in ("boothNo", "boothNum"):
            if ec.get(key):
                raw_booths.append(str(ec[key]))
        for b in raw_booths:
            for part in re.split(r"[,，]+", b):
                tok = part.strip()
                if tok and tok not in booth_tokens:
                    booth_tokens.append(tok)

        category = clean_text(
            ec.get("categoryNameEn")
            or ec.get("exhiCorpOneCategoryEn")
            or ec.get("categoryName")
            or ec.get("exhiCorpOneCategory")
        )
        location = clean_text(ec.get("enRegisterAddress") or ec.get("registerAddress"))
        website = clean_text(ec.get("enWebsite") or ec.get("website"))
        profile = clean_text(ec.get("englishIntroduced") or "")

        product_names = []
        for p in products_list:
            name = clean_text(p.get("exhibitsEnName") or p.get("exhibitsName"))
            if name and name not in product_names:
                product_names.append(name)

        output_rows.append({
            "URL": row["URL"],
            "Exhibitor Name (English)": row["Exhibitor Name (English)"],
            "Booth": ", ".join(booth_tokens),
            "Zone": row.get("Zone", ""),
            "Category": category,
            "Location": location,
            "Website": website,
            "Featured Products": " | ".join(product_names),
            "Company Profile": profile,
        })

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Done! Saved {len(output_rows)} rows to {OUTPUT_CSV} (errors: {len(errors)})")


if __name__ == "__main__":
    main()