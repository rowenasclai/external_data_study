#!/usr/bin/env python3
"""Normalize HKAA and GLD evidence captured by the _hermes extractors.

The normalizer is deterministic and fail-visible: unmatched records are retained in
normalization_rejects.json and cause a non-zero exit instead of being invented.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DATA_DIR = Path(os.environ["GOV_HERMES_DATA_DIR"]).resolve()

MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_RE = re.compile(rf"(\d{{1,2}}\s+{MONTH}\s+\d{{4}})\b", re.I)
AMOUNT_RE = re.compile(r"\b(?:HK\$|HKD\s*|\$)\s*[\d,]+(?:\.\d+)?\b", re.I)
COMPANY_END = re.compile(
    r"\b(?:Limited|Ltd\.?|Company|Corporation|Holdings|Consortium|Joint Venture|JV|Association)\b",
    re.I,
)


def json_lines(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path.name}:{number}: expected object")
            rows.append(value)
    return rows


def write_json_lines(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return [value]
        return flatten_strings(decoded)
    if isinstance(value, dict):
        out: list[str] = []
        for child in value.values():
            out.extend(flatten_strings(child))
        return out
    if isinstance(value, list):
        out = []
        for child in value:
            out.extend(flatten_strings(child))
        return out
    return []


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def iso_date(value: str) -> str:
    parsed = datetime.strptime(value, "%d %B %Y") if len(value.split()[1]) > 3 else datetime.strptime(value, "%d %b %Y")
    return parsed.strftime("%Y-%m-%d")


def short_date(value: str) -> str:
    parsed = datetime.strptime(value, "%d %B %Y") if len(value.split()[1]) > 3 else datetime.strptime(value, "%d %b %Y")
    return parsed.strftime("%d %b %Y")


def normalize_hkaa(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    text = clean(" ".join(flatten_strings(raw.get("extracted_content")) + [str(raw.get("markdown") or "")]))
    date_match = DATE_RE.search(text)
    amount_match = AMOUNT_RE.search(text)
    party_match = re.search(r"\bto\s+(.+?)\s+of\s+(.+?)\s+on\s+" + DATE_RE.pattern, text, re.I)
    if not date_match or not amount_match or not party_match:
        return None, "missing awardee/address/date/amount pattern"
    ref = clean(raw.get("ref"))
    record = {
        "ref": ref,
        "department": "Hong Kong Airport Authority",
        "description": clean(raw.get("description")),
        "awardee": clean(party_match.group(1)),
        "contractor_address": clean(party_match.group(2)),
        "award_date": iso_date(date_match.group(1)),
        "sum": clean(amount_match.group(0)),
        "period": "",
        "url": clean(raw.get("url")),
        "start": "",
        "end": "",
        "type": clean(raw.get("type")),
    }
    if not all(record[key] for key in ("ref", "awardee", "award_date", "sum", "url")):
        return None, "required normalized field empty"
    return record, None


def split_contractor(value: Any) -> tuple[str, str]:
    text = str(value or "").strip()
    text = re.sub(r"^\(\d+\)\s*", "", text)
    lines = [clean(line) for line in re.split(r"[\r\n]+", text) if clean(line)]
    if len(lines) > 1:
        return lines[0], clean(" ".join(lines[1:]))
    compact = clean(text)
    match = COMPANY_END.search(compact)
    if match:
        return compact[: match.end()].strip(" ,;"), compact[match.end() :].strip(" ,;")
    return compact, ""


def normalize_gld(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    contractor = raw.get("Contractor(s) & Address(es)")
    amount_date = clean(raw.get("Amount / Contract Award Date"))
    if not contractor and not amount_date:
        return None, "skip: section or department header"
    awardee, address = split_contractor(contractor)
    date_match = DATE_RE.search(amount_date)
    amount_match = AMOUNT_RE.search(amount_date)
    explicit_non_monetary = amount_date.lower().startswith("not applicable")
    if not awardee or not date_match or (not amount_match and not explicit_non_monetary):
        return None, "missing contractor/date/amount pattern"
    amount = clean(amount_date[: date_match.start()])
    record = dict(raw)
    record.update(
        {
            "awardee": awardee,
            "contractor_address": address,
            "award_date": short_date(date_match.group(1)),
            "sum": amount,
            "url": "https://pcms2.gld.gov.hk/iprod/#/scn00101",
            "period": clean(raw.get("period")),
            "start": clean(raw.get("start")),
            "end": clean(raw.get("end")),
        }
    )
    return record, None


def main() -> int:
    normalized_hkaa: list[dict[str, Any]] = []
    normalized_gld: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for index, raw in enumerate(json_lines(DATA_DIR / "gov_hkaa_unstructured.json"), 1):
        record, error = normalize_hkaa(raw)
        if record is None:
            rejects.append({"source": "hkaa", "index": index, "error": error, "raw": raw})
        else:
            normalized_hkaa.append(record)

    # GLD uses rowspans. Continuation rows carry contractor and amount/date but
    # inherit the reference and description from the preceding primary row.
    context: dict[str, Any] | None = None
    for index, original in enumerate(json_lines(DATA_DIR / "gov_gld_unstructured.json"), 1):
        raw = dict(original)
        contractor = raw.get("Contractor(s) & Address(es)")
        amount_date = raw.get("Amount / Contract Award Date")
        if contractor and amount_date and not clean(raw.get("ref")).startswith("("):
            context = {
                "ref": raw.get("ref"),
                "particulars": raw.get("particulars"),
                "tendering_procedure": raw.get("tendering_procedure"),
            }
        elif contractor and not amount_date and AMOUNT_RE.search(clean(raw.get("particulars"))):
            if context is None:
                rejects.append({"source": "gld", "index": index, "error": "continuation row lacks primary context", "raw": original})
                continue
            raw["Amount / Contract Award Date"] = raw.get("particulars")
            raw["particulars"] = context.get("particulars")
            raw["ref"] = context.get("ref")
            raw["period"] = raw.get("tendering_procedure") or context.get("tendering_procedure")
        record, error = normalize_gld(raw)
        if record is None and error and error.startswith("skip:"):
            skipped.append({"source": "gld", "index": index, "reason": error, "raw": original})
        elif record is None:
            rejects.append({"source": "gld", "index": index, "error": error, "raw": original})
        else:
            normalized_gld.append(record)
    write_json_lines(DATA_DIR / "gov_hkaa.json", normalized_hkaa)
    write_json_lines(DATA_DIR / "gov_gld.json", normalized_gld)
    write_json_lines(DATA_DIR / "normalization_rejects.json", rejects)
    write_json_lines(DATA_DIR / "normalization_skipped.json", skipped)
    summary = {"hkaa": len(normalized_hkaa), "gld": len(normalized_gld), "skipped": len(skipped), "rejects": len(rejects)}
    print(json.dumps(summary, sort_keys=True))
    return 1 if rejects else 0


if __name__ == "__main__":
    raise SystemExit(main())
