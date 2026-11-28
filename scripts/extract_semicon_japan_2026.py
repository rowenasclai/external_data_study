#!/usr/bin/env python3
"""Public SEMICON Japan 2026 exhibitor directory extractor."""
from __future__ import annotations
import argparse, csv, html, json, os, re, time
from http.cookiejar import CookieJar
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import unquote, urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

LISTING_URL = "https://portal2026.semiconjapan.org/exhibitors"
AJAX_URL = "https://portal2026.semiconjapan.org/index.php"
PAGE_SIZE = 50
FIELDS = ["exhibitor_id", "company_name", "booth", "detail_url", "source_url", "source_position"]
USER_AGENT = "external-data-study-semicon-japan-2026/1.0"

class ExtractionError(RuntimeError): pass

def text(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())

def parse_rows(markup: str, source_position_start: int = 1) -> list[dict[str, str]]:
    rows = []
    for chunk in re.findall(r"<tr\b[^>]*>(.*?)</tr>", markup, flags=re.I | re.S):
        match = re.search(r'data-option-item-id="(\d+)"', chunk)
        link = re.search(r'<a\b[^>]*href="(/(?:exhibitors/exhibitor/\d+|co/[^"?#]+))"[^>]*>(.*?)</a>', chunk, flags=re.I | re.S)
        if not match or not link:
            continue
        name = text(link.group(2))
        if not name:
            raise ExtractionError(f"missing company name for ID {match.group(1)}")
        booth_match = re.search(r"MapItBooth=([^&\"']+)", chunk)
        rows.append({
            "exhibitor_id": match.group(1), "company_name": name,
            "booth": html.unescape(booth_match.group(1)) if booth_match else "",
            "detail_url": urljoin(LISTING_URL, html.unescape(link.group(1))),
            "source_url": LISTING_URL, "source_position": str(source_position_start + len(rows)),
        })
    return rows

def tokens(markup: str) -> tuple[str, str]:
    tk = re.search(r"var tk='([^']+)'", markup)
    tm = re.search(r"var tm='([^']+)'", markup)
    if not tk or not tm: raise ExtractionError("public listing omitted required pagination form state")
    return tk.group(1), tm.group(1)

def response_rows(payload: dict, start: int) -> tuple[list[dict[str, str]], int]:
    if not isinstance(payload.get("total"), int) or payload["total"] < 1:
        raise ExtractionError("pagination response omitted a positive total")
    encoded = payload.get("data")
    if not isinstance(encoded, str): raise ExtractionError("pagination response omitted HTML data")
    rows = parse_rows(unquote(encoded), start)
    if not rows: raise ExtractionError("nonzero total with empty page")
    return rows, payload["total"]

def get_all(timeout: int = 30, delay: float = .15) -> tuple[list[dict[str, str]], int]:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    headers = {"User-Agent": USER_AGENT}
    listing = opener.open(Request(LISTING_URL, headers=headers), timeout=timeout).read().decode("utf-8", "replace")
    tk, tm = tokens(listing)
    all_rows: list[dict[str, str]] = []
    total = None
    for offset in range(0, 1000000, PAGE_SIZE):
        form = {"module":"organizations_organization_list", "site_page_id":"3000", "method":"paginationHandler", "template":"generic_items", "mCell":"4_0", "mId":"0", "limit":str(PAGE_SIZE), "offset":str(offset), "page_id":"openAjax", "ajaxType":"paginate", "tk":tk, "tm":tm}
        request = Request(AJAX_URL, data=urlencode(form).encode(), headers={**headers, "Referer":LISTING_URL, "Content-Type":"application/x-www-form-urlencoded"})
        raw = opener.open(request, timeout=timeout).read().decode("utf-8", "replace")
        try: payload = json.loads(raw)
        except json.JSONDecodeError as exc: raise ExtractionError(f"page offset {offset}: malformed JSON") from exc
        page, page_total = response_rows(payload, offset + 1)
        if total is None: total = page_total
        elif total != page_total: raise ExtractionError(f"inconsistent total at offset {offset}: {page_total} != {total}")
        if offset + len(page) < total and len(page) != PAGE_SIZE:
            raise ExtractionError(f"short interior page at offset {offset}: {len(page)}")
        all_rows.extend(page)
        if len(all_rows) >= total: break
        tk, tm = payload.get("formToken", tk), payload.get("formTime", tm)
        time.sleep(delay)
    if total is None or len(all_rows) != total: raise ExtractionError(f"coverage mismatch: got {len(all_rows)}, expected {total}")
    ids = [r["exhibitor_id"] for r in all_rows]
    if len(set(ids)) != len(ids): raise ExtractionError("duplicate stable exhibitor IDs")
    return all_rows, total

def atomic_write(path: Path, content: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as f:
        f.write(content); f.flush(); os.fsync(f.fileno()); temporary = Path(f.name)
    temporary.replace(path)

def write_outputs(rows: list[dict[str,str]], csv_path: Path, json_path: Path) -> None:
    import io
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    atomic_write(csv_path, buf.getvalue(), "utf-8-sig")
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")

def validate(csv_path: Path, json_path: Path, total: int) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as f: csv_rows=list(csv.DictReader(f))
    json_rows=json.loads(json_path.read_text(encoding="utf-8"))
    if len(csv_rows) != total or csv_rows != json_rows: raise ExtractionError("CSV/JSON read-back mismatch")
    if [r["exhibitor_id"] for r in csv_rows] != [r["exhibitor_id"] for r in json_rows]: raise ExtractionError("stable ID sequence mismatch")

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--json-output", type=Path, required=True); args=parser.parse_args()
    rows,total=get_all(); write_outputs(rows,args.output,args.json_output); validate(args.output,args.json_output,total)
    print(f"records={total} csv={args.output} json={args.json_output}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
