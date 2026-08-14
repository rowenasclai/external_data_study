#!/usr/bin/env python3
"""Isolated Linux dry-run controller for government contract extraction.

This _hermes copy never deletes or overwrites the original tracked Raw/data files.
Each run receives a timestamped workspace, per-stage logs, and an atomic manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = REPO_ROOT / "Result" / "Government Contract Extraction" / "gov_cntract"
DRY_RUN_ROOT = RESULT_ROOT / "hermes_dry_runs"

EXTRACTORS = [
    ("epd", "epd_hermes.py", ["gov_epd.json"]),
    ("dsd", "dsd_hermes.py", ["gov_dsd.json"]),
    ("cedd", "cedd_hermes.py", ["gov_cedd.json"]),
    ("cedd_consultant", "cedd_consultant_hermes.py", ["gov_cedd_consultant.json"]),
    ("emsd_award", "emsd_award_hermes.py", ["gov_emsd.json"]),
    ("emsd_construction", "emsd_award_construction_hermes.py", ["gov_emsd_construction.json"]),
    ("hkaa", "hkaa_hermes.py", ["gov_hkaa_unstructured.json"]),
    ("hyd", "hyd_hermes.py", ["gov_hyd.json"]),
    ("wsd", "wsd_hermes.py", ["gov_wsd.json"]),
    ("wsd_consultant", "wsd_consultant_hermes.py", ["gov_wsd_consultant.json"]),
    ("td", "td_hermes.py", ["gov_td.json", "gov_td_consultant.json"]),
    ("gld", "gld_hermes.py", ["gov_gld_unstructured.json"]),
]


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_count(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for line in handle if line.strip())


def run_stage(name: str, script: str, expected: list[str], env: dict[str, str], logs: Path, timeout: int) -> dict[str, object]:
    started = datetime.now().astimezone().isoformat()
    command = [sys.executable, str(SCRIPT_DIR / script)]
    result: dict[str, object] = {"name": name, "script": script, "started_at": started, "command": command}
    try:
        completed = subprocess.run(command, cwd=SCRIPT_DIR, env=env, capture_output=True, timeout=timeout)
        (logs / f"{name}.stdout.log").write_bytes(completed.stdout)
        (logs / f"{name}.stderr.log").write_bytes(completed.stderr)
        result["returncode"] = completed.returncode
    except subprocess.TimeoutExpired as exc:
        (logs / f"{name}.stdout.log").write_bytes(exc.stdout or b"")
        (logs / f"{name}.stderr.log").write_bytes(exc.stderr or b"")
        result["returncode"] = 124
        result["error"] = f"timeout after {timeout}s"
    outputs = []
    for filename in expected:
        path = Path(env["GOV_HERMES_DATA_DIR"]) / filename
        outputs.append({
            "name": filename,
            "exists": path.is_file(),
            "size": path.stat().st_size if path.is_file() else 0,
            "rows": line_count(path) if path.is_file() else 0,
            "sha256": sha256(path) if path.is_file() else None,
        })
    result["outputs"] = outputs
    result["finished_at"] = datetime.now().astimezone().isoformat()
    result["status"] = "passed" if result.get("returncode") == 0 and all(item["exists"] and item["rows"] for item in outputs) else "failed"
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", help="existing/new run ID; default is timestamped")
    parser.add_argument("--phase", choices=("all", "extract", "normalize", "format"), default="all")
    parser.add_argument("--stage-timeout", type=int, default=1800)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id or datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-hermes")
    run_dir = DRY_RUN_ROOT / run_id
    data_dir = run_dir / "Raw" / "data"
    logs = run_dir / "logs"
    output = RESULT_ROOT / f"gov_cntract_{run_id}.csv"
    manifest_path = run_dir / "manifest.json"

    if args.phase in ("all", "extract") and run_dir.exists():
        raise SystemExit(f"refusing to append to existing extraction run: {run_dir}")
    data_dir.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["GOV_HERMES_DATA_DIR"] = str(data_dir)
    env["GOV_HERMES_OUTPUT_FILE"] = str(output)

    if manifest_path.exists() and args.phase in ("normalize", "format"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.setdefault("resume_events", []).append(
            {"phase": args.phase, "started_at": datetime.now().astimezone().isoformat()}
        )
        manifest["phase"] = args.phase
        manifest["status"] = "running"
        manifest.pop("finished_at", None)
    else:
        manifest = {
            "run_id": run_id,
            "phase": args.phase,
            "status": "running",
            "started_at": datetime.now().astimezone().isoformat(),
            "run_dir": str(run_dir.relative_to(REPO_ROOT)),
            "output": str(output.relative_to(REPO_ROOT)),
            "stages": [],
            "resume_events": [],
        }
    atomic_json(manifest_path, manifest)

    if args.phase in ("all", "extract"):
        for name, script, expected in EXTRACTORS:
            stage = run_stage(name, script, expected, env, logs, args.stage_timeout)
            manifest["stages"].append(stage)
            atomic_json(manifest_path, manifest)
        if any(stage["status"] != "passed" for stage in manifest["stages"]):
            manifest["status"] = "extraction_failed"
            manifest["finished_at"] = datetime.now().astimezone().isoformat()
            atomic_json(manifest_path, manifest)
            print(json.dumps({"run_id": run_id, "status": manifest["status"], "run_dir": str(run_dir)}))
            return 1
        if args.phase == "extract":
            manifest["status"] = "extracted"
            manifest["finished_at"] = datetime.now().astimezone().isoformat()
            atomic_json(manifest_path, manifest)
            print(json.dumps({"run_id": run_id, "status": manifest["status"], "run_dir": str(run_dir)}))
            return 0

    if args.phase in ("all", "normalize"):
        stage = run_stage(
            "normalize_unstructured",
            "normalize_unstructured_hermes.py",
            ["gov_hkaa.json", "gov_gld.json", "normalization_rejects.json", "normalization_skipped.json"],
            env,
            logs,
            args.stage_timeout,
        )
        # An empty reject file is valid and desirable.
        reject_output = next(item for item in stage["outputs"] if item["name"] == "normalization_rejects.json")
        normalized_outputs = [item for item in stage["outputs"] if item["name"] in ("gov_hkaa.json", "gov_gld.json")]
        if reject_output["exists"] and reject_output["rows"] == 0 and stage.get("returncode") == 0 and all(item["rows"] > 0 for item in normalized_outputs):
            stage["status"] = "passed"
        manifest["stages"].append(stage)
        if stage["status"] != "passed":
            manifest["status"] = "normalization_failed"
            manifest["finished_at"] = datetime.now().astimezone().isoformat()
            atomic_json(manifest_path, manifest)
            print(json.dumps({"run_id": run_id, "status": manifest["status"], "run_dir": str(run_dir)}))
            return 1
        if args.phase == "normalize":
            manifest["status"] = "normalized"
            manifest["finished_at"] = datetime.now().astimezone().isoformat()
            atomic_json(manifest_path, manifest)
            print(json.dumps({"run_id": run_id, "status": manifest["status"], "run_dir": str(run_dir)}))
            return 0

    if args.phase in ("all", "format"):
        stage = run_stage("format", "gov_format_hermes.py", [], env, logs, args.stage_timeout)
        stage["outputs"] = [{
            "name": output.name,
            "exists": output.is_file(),
            "size": output.stat().st_size if output.is_file() else 0,
            "rows": line_count(output) - 1 if output.is_file() else 0,
            "sha256": sha256(output) if output.is_file() else None,
        }]
        stage["status"] = "passed" if stage.get("returncode") == 0 and output.is_file() and stage["outputs"][0]["rows"] > 0 else "failed"
        manifest["stages"].append(stage)
        manifest["status"] = "completed" if stage["status"] == "passed" else "format_failed"

    manifest["finished_at"] = datetime.now().astimezone().isoformat()
    atomic_json(manifest_path, manifest)
    print(json.dumps({"run_id": run_id, "status": manifest["status"], "run_dir": str(run_dir), "output": str(output)}))
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
