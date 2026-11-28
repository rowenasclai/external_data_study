import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_control_sheet as updater  # noqa: E402


STATUS_CASES = [
    "Agent Extraction",
    "Fail",
    "No Exhibitor List",
    "Scope Mismatch",
    "Visible method not available",
]


def write_manifest(path: Path, updates: list[dict]) -> Path:
    path.write_text(
        json.dumps({"schema_version": 1, "updates": updates}), encoding="utf-8"
    )
    return path


class UpdateControlSheetTests(unittest.TestCase):
    def test_all_approved_statuses_and_filename_rules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for status in STATUS_CASES:
                with self.subTest(status=status):
                    filename = "sample.csv" if status == "Agent Extraction" else ""
                    path = write_manifest(
                        Path(temp_dir) / f"{status}.json",
                        [{"event_name": "Example Event", "status": status, "extracted_file_name": filename}],
                    )
                    self.assertEqual(
                        updater.load_requested_updates([path]),
                        {"Example Event": (status, filename)},
                    )

    def test_unknown_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_manifest(
                Path(temp_dir) / "manifest.json",
                [{"event_name": "Example Event", "status": "Unknown", "extracted_file_name": ""}],
            )
            with self.assertRaisesRegex(ValueError, "unapproved status"):
                updater.load_requested_updates([path])

    def test_non_extraction_status_cannot_claim_output_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_manifest(
                Path(temp_dir) / "manifest.json",
                [{"event_name": "Example Event", "status": "Scope Mismatch", "extracted_file_name": "sample.csv"}],
            )
            with self.assertRaisesRegex(ValueError, "all other statuses require it to be blank"):
                updater.load_requested_updates([path])

    def test_duplicate_event_across_manifests_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            item = {"event_name": "Example Event", "status": "Fail", "extracted_file_name": ""}
            first = write_manifest(Path(temp_dir) / "first.json", [item])
            second = write_manifest(Path(temp_dir) / "second.json", [item])
            with self.assertRaisesRegex(ValueError, "duplicate event"):
                updater.load_requested_updates([first, second])

    def test_main_writes_requested_reason_status(self):
        class Request:
            def __init__(self, value):
                self.value = value

            def execute(self):
                return self.value

        class Values:
            def __init__(self):
                self.batch = None

            def get(self, **kwargs):
                return Request({"values": [
                    ["Event Name", "Status", "Extracted File Name"],
                    ["Example Event", "New", ""],
                ]})

            def batchUpdate(self, **kwargs):
                self.batch = kwargs
                return Request({})

        class Spreadsheets:
            def __init__(self):
                self._values = Values()

            def get(self, **kwargs):
                return Request({"sheets": [{"properties": {"title": "Events", "sheetType": "GRID"}}]})

            def values(self):
                return self._values

        sheets = Spreadsheets()
        fake_service = type("Service", (), {"spreadsheets": lambda self: sheets})()
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = write_manifest(
                Path(temp_dir) / "manifest.json",
                [{"event_name": "Example Event", "status": "Visible method not available", "extracted_file_name": ""}],
            )
            env = {
                "GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON": '{"client_email":"test@example.invalid"}',
                "CONTROL_MANIFESTS": str(manifest),
            }
            with mock.patch.dict("os.environ", env, clear=False), \
                 mock.patch.object(updater.Credentials, "from_service_account_info", return_value=object()), \
                 mock.patch.object(updater, "build", return_value=fake_service), \
                 mock.patch("builtins.print") as printed:
                self.assertEqual(updater.main(), 0)

        self.assertEqual(sheets._values.batch["body"]["data"], [
            {"range": "'Events'!B2", "values": [["Visible method not available"]]},
            {"range": "'Events'!C2", "values": [[""]]}
        ])
        printed.assert_called_once_with('{"updated_events": ["Example Event"], "cells_updated": 2}')


if __name__ == "__main__":
    unittest.main()
