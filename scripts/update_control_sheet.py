#!/usr/bin/env python3
"""Update approved control-sheet completion fields from a committed manifest."""
from __future__ import annotations

import json
import os
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = "1WJHV8bBeiCJbY-zo5zFDUuYoUH_LNXPHuIqUlPqP0II"
HEADERS = {"Event Name", "Status", "Extracted File Name"}
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main() -> int:
    manifest_path = Path(os.environ.get("COMPLETION_MANIFEST", "Result/Exhibition Organizers/completion_manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    updates = manifest.get("updates")
    if manifest.get("schema_version") != 1 or not isinstance(updates, list) or not updates:
        raise ValueError("invalid completion manifest")

    requested = {}
    for item in updates:
        if set(item) != {"event_name", "status", "extracted_file_name"}:
            raise ValueError("manifest item has unexpected fields")
        name, status, filename = (str(item[key]).strip() for key in ("event_name", "status", "extracted_file_name"))
        if not name or status != "Done" or not filename or "/" in filename or "\\" in filename:
            raise ValueError("only non-empty filename and New -> Done updates are permitted")
        if name in requested:
            raise ValueError(f"duplicate event in manifest: {name}")
        requested[name] = filename

    credentials_data = json.loads(os.environ["GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON"])
    credentials = Credentials.from_service_account_info(credentials_data, scopes=SCOPES)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()

    found = set()
    batch = []
    for sheet in spreadsheet["sheets"]:
        title = sheet["properties"]["title"]
        values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{title}'!A:Z").execute().get("values", [])
        for index, row in enumerate(values):
            if not HEADERS.issubset(set(row)):
                continue
            event_col = row.index("Event Name")
            status_col = row.index("Status")
            file_col = row.index("Extracted File Name")
            for row_number, record in enumerate(values[index + 1 :], start=index + 2):
                event_name = record[event_col].strip() if len(record) > event_col else ""
                if event_name not in requested:
                    continue
                current_status = record[status_col].strip() if len(record) > status_col else ""
                if current_status != "New":
                    raise ValueError(f"refusing to overwrite {event_name!r} with current status {current_status!r}")
                for column, value in ((status_col, "Done"), (file_col, requested[event_name])):
                    letter = chr(ord("A") + column)
                    batch.append({"range": f"'{title}'!{letter}{row_number}", "values": [[value]]})
                found.add(event_name)
            break

    missing = set(requested) - found
    if missing:
        raise ValueError(f"events not found in New status: {sorted(missing)}")
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"valueInputOption": "RAW", "data": batch},
    ).execute()
    print(json.dumps({"updated_events": sorted(found), "cells_updated": len(batch)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
