#!/usr/bin/env python3
"""Regression tests for terminal handling of transient HKTDC public failures."""
from __future__ import annotations

import importlib.util
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "PY" / "Event Organizer-hermes" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def failing_urlopen(request, timeout):
    raise HTTPError(request.full_url, 504, "Gateway Time-out", Message(), None)


def test_l2_504_is_checkpointable_terminal_outcome():
    module = load("hktdc_l2", "hktdc_exhibit_L2_hermes.py")
    setattr(module, "urlopen", failing_urlopen)
    setattr(module.time, "sleep", lambda _seconds: None)
    record = module.fetch_one({"Company Name": "Example Co", "Location": "Hong Kong", "url": "/event/demo/en/exhibitor/abc"})
    assert record["l2_status"] == "request_error_http_504"
    assert record["source_company_name"] == "Example Co"
    assert record["exhibitor_url"] == "https://www.hktdc.com/event/demo/en/exhibitor/abc"


def test_l3_504_is_checkpointable_terminal_outcome():
    module = load("hktdc_l3", "hktdc_exhibit_L3_hermes.py")
    setattr(module, "urlopen", failing_urlopen)
    setattr(module.time, "sleep", lambda _seconds: None)
    record = module.fetch_one({"source_company_name": "Example Co", "supplier_url": "https://sourcing.hktdc.com/en/Supplier-Store/Profile/Example/abc", "l2_status": "extracted"})
    assert record["l3_status"] == "request_error_http_504"
    assert record["source_company_name"] == "Example Co"
    assert record["supplier_url"] == "https://sourcing.hktdc.com/en/Supplier-Store/Profile/Example/abc"


if __name__ == "__main__":
    test_l2_504_is_checkpointable_terminal_outcome()
    test_l3_504_is_checkpointable_terminal_outcome()
    print("2 HKTDC terminal-outcome regression tests passed")
