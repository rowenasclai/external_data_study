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
ALLOWED_STATUSES = {
    "Done",
    "Blocked: access denied (HTTP 403)",
    "No public directory: supplied URL is not a directory",
    "Invalid directory URL: page is for 2027",
    "No current 2026 directory: official list is for 2024",
    "Invalid directory URL: supplied page is an event overview",
}
REOPENABLE_COMPLETIONS = {
    (
        "Taiwan Innotech Expo 2026 (TIE 2026)",
        "No current 2026 directory: official list is for 2024",
    ),
}
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main() -> int:
    manifest_paths = [
        Path(path.strip())
        for path in os.environ.get(
            "CONTROL_MANIFESTS",
            "Result/Exhibition Organizers/completion_manifest.json",
        ).split(",")
        if path.strip()
    ]
    requested = {}
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        updates = manifest.get("updates")
        if manifest.get("schema_version") != 1 or not isinstance(updates, list) or not updates:
            raise ValueError(f"invalid control manifest: {manifest_path}")
        for item in updates:
            if set(item) != {"event_name", "status", "extracted_file_name"}:
                raise ValueError("manifest item has unexpected fields")
            name, status, filename = (str(item[key]).strip() for key in ("event_name", "status", "extracted_file_name"))
            if not name or status not in ALLOWED_STATUSES or "/" in filename or "\\" in filename:
                raise ValueError("manifest contains an unapproved status or filename")
            if (status == "Done") != bool(filename):
                raise ValueError("Done requires a filename; terminal outcomes require it to be blank")
            if name in requested:
                raise ValueError(f"duplicate event in control manifests: {name}")
            requested[name] = (status, filename)

    credentials_data = json.loads(os.environ["GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON"])
    # GitHub secrets should contain the JSON object directly. Accept one extra
    # JSON string layer so a harmlessly quoted/escaped secret fails neither
    # cryptically nor by attempting to use a string as credential metadata.
    if isinstance(credentials_data, str):
        credentials_data = json.loads(credentials_data)
    if not isinstance(credentials_data, dict):
        raise ValueError("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON must decode to a JSON object")
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
                target_status, target_filename = requested[event_name]
                current_status = record[status_col].strip() if len(record) > status_col else ""
                current_filename = record[file_col].strip() if len(record) > file_col else ""
                if current_status == target_status and current_filename == target_filename:
                    found.add(event_name)
                    continue
                reopenable = target_status == "Done" and (event_name, current_status) in REOPENABLE_COMPLETIONS
                if current_status != "New" and not reopenable:
                    raise ValueError(f"refusing to overwrite {event_name!r} with current status {current_status!r}")
                for column, value in ((status_col, target_status), (file_col, target_filename)):
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
