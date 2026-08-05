#!/usr/bin/env python3
"""
Extract the full exhibitor list from the CCMT/CIMT exhibitor iframe app.

Default target is the CCMT English exhibitor list currently embedded at:
https://www.ccmtshow.com/en/339/list.html

Requirements:
    pip install requests cryptography

Examples:
    python extract_ccmt_exhibitors.py
    python extract_ccmt_exhibitors.py --output exhibitors.csv
    python extract_ccmt_exhibitors.py --json-output exhibitors.json
    python extract_ccmt_exhibitors.py --show-type ccmt --lang en
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import random
import re
import string
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

API_URL = "https://service.cmtba.org.cn/api/cmtbashow_q"
REFERER = "https://es.cmtba.org.cn/"
ORIGIN = "https://es.cmtba.org.cn"

# This is embedded in the site's JS bundle. The frontend encrypts/decrypts API
# payloads with AES-ECB + PKCS#7 padding and prefixes plaintext with timestamp|.
AES_KEY = b"80081695d14211ed887300163e321ce3"


def pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        raise ValueError("Cannot unpad empty data")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError("Invalid PKCS#7 padding")
    return data[:-pad_len]


def aes_ecb(data: bytes, encrypt: bool) -> bytes:
    cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
    ctx = cipher.encryptor() if encrypt else cipher.decryptor()
    return ctx.update(data) + ctx.finalize()


def encrypt_payload(payload: Dict[str, Any]) -> str:
    plaintext = f"{int(time.time() * 1000)}|" + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )
    encrypted = aes_ecb(pkcs7_pad(plaintext.encode("utf-8")), encrypt=True)
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_response(ciphertext_b64: str) -> Any:
    decrypted = aes_ecb(base64.b64decode(ciphertext_b64), encrypt=False)
    plaintext = pkcs7_unpad(decrypted).decode("utf-8")
    if "|" not in plaintext:
        raise ValueError("Unexpected decrypted response format")
    return json.loads(plaintext.split("|", 1)[1])


def encrypted_post(payload: Dict[str, Any], timeout: int = 90) -> Any:
    random_key = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
    body = {random_key: encrypt_payload(payload)}
    response = requests.post(
        API_URL,
        json=body,
        headers={
            "Origin": ORIGIN,
            "Referer": REFERER,
            "User-Agent": "Mozilla/5.0 exhibitor-extractor/1.0",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return decrypt_response(response.text)


def get_show_metadata(show_type: str) -> Dict[str, Any]:
    payload = {
        "TableName": "",
        "Fields": "",
        "OrderBy": "",
        "Where": "",
        "ProName": "sp_get_cmtbashow_maininfo",
        "ProPara": show_type,
        "Type": 1,
        "PageIndex": 1,
        "PageSize": 0,
    }
    result = encrypted_post(payload)
    if result[0]:
        raise RuntimeError(f"API error getting show metadata: {result[0]}")
    data = result[1]
    return {
        "expo_show_id": data["Table"][0]["expo_show_id"],
        "show_name_cn": data["Table"][0].get("expo_show_zhqc_cn", ""),
        "show_name_en": data["Table"][0].get("expo_show_zhqc_en", ""),
        "viewname": data["Table1"][0]["viewname"],
        "sortfield": data["Table1"][0].get("sortfield") or "展位号",
        "sorttype": data["Table1"][0].get("sorttype") or "Asc",
        "raw": data,
    }


def parse_pidarr(pidarr: str, key: str) -> int | str:
    # The site returns strings like:
    # {expo_enterprises_exhibit_id:17683,expo_enterprises_id:156,...}
    match = re.search(r"\b" + re.escape(key) + r":(\d+)", pidarr or "")
    return int(match.group(1)) if match else ""


def fetch_exhibitors(show_type: str = "ccmt", page_size: int = 5000) -> List[Dict[str, Any]]:
    meta = get_show_metadata(show_type)
    payload = {
        "TableName": meta["viewname"],
        "Fields": "",
        "OrderBy": f"{meta['sortfield']} {meta['sorttype']}",
        "Where": f"expo_show_id = {meta['expo_show_id']}",
        "ProName": "",
        "ProPara": "",
        "Type": 0,
        "PageIndex": 1,
        "PageSize": page_size,
    }
    result = encrypted_post(payload)
    if result[0]:
        raise RuntimeError(f"API error getting exhibitors: {result[0]}")

    data = result[1]
    rows = data.get("Table", [])
    total = data.get("Table1", [{}])[0].get("totalcount", len(rows))

    # If the page_size was too small, fetch again with the exact total.
    if len(rows) < total:
        payload["PageSize"] = total
        result = encrypted_post(payload)
        if result[0]:
            raise RuntimeError(f"API error getting full exhibitors: {result[0]}")
        data = result[1]
        rows = data.get("Table", [])

    normalized = []
    for row in rows:
        pidarr = row.get("pidarr", "")
        normalized.append(
            {
                "booth_no": row.get("展位号", ""),
                "company_name_cn": row.get("中文名", ""),
                "company_name_en": row.get("英文名", ""),
                "expo_show_id": row.get("expo_show_id", meta["expo_show_id"]),
                "expo_enterprises_exhibit_id": parse_pidarr(pidarr, "expo_enterprises_exhibit_id"),
                "expo_enterprises_id": parse_pidarr(pidarr, "expo_enterprises_id"),
                "expo_manual_form_exhibit_id": parse_pidarr(pidarr, "expo_manual_form_exhibit_id"),
            }
        )
    return normalized


def write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        raise ValueError("No rows to write")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: List[Dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract CCMT/CIMT exhibitor list")
    parser.add_argument("--show-type", default="ccmt", help="Show type query value, default: ccmt")
    parser.add_argument("--output", default="ccmt_exhibitors.csv", help="CSV output path")
    parser.add_argument("--json-output", default="", help="Optional JSON output path")
    parser.add_argument("--page-size", type=int, default=5000, help="Initial API page size")
    args = parser.parse_args()

    rows = fetch_exhibitors(show_type=args.show_type, page_size=args.page_size)
    write_csv(rows, Path(args.output))
    if args.json_output:
        write_json(rows, Path(args.json_output))

    print(f"Extracted {len(rows)} exhibitors")
    print(f"CSV: {Path(args.output).resolve()}")
    if args.json_output:
        print(f"JSON: {Path(args.json_output).resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
