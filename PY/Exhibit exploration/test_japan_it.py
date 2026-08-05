"""
Tests for japan_it.py - Japan IT Week Spring 2026 Exhibitor Scraper

These tests are isolated and deterministic, using mocked Playwright objects
so they do not require actual browser launches or network access.

Run with: pytest PY/test_japan_it.py -v
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Import functions under test
from japan_it import (
    _dismiss_cookie_banner,
    _safe_text,
    _safe_attr,
    _write_record,
    scrape_directory,
    scrape_exhibitor_details,
    BASE_URL,
    OUTPUT_FILE,
    OUTPUT_DETAIL_FILE,
)


# ──────────────────────────────────────────────────────────────────────
# Helper: mock Playwright objects
# ──────────────────────────────────────────────────────────────────────
def _mock_page():
    """Create a mock Playwright page with common methods."""
    page = MagicMock()
    page.goto = MagicMock()
    page.wait_for_load_state = MagicMock()
    page.wait_for_timeout = MagicMock()
    page.locator = MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
    page.get_by_role = MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
    return page


def _mock_locator(count=1, text="Sample Text", attr_val="https://example.com"):
    """Create a mock locator that returns controlled values."""
    loc = MagicMock()
    loc.count = MagicMock(return_value=count)
    loc.first = MagicMock()
    loc.first.inner_text = MagicMock(return_value=text)
    loc.first.get_attribute = MagicMock(return_value=attr_val)
    loc.first.click = MagicMock()
    loc.first.is_enabled = MagicMock(return_value=True)
    loc.inner_text = MagicMock(return_value=text)
    loc.nth = MagicMock(return_value=loc)
    return loc


# ──────────────────────────────────────────────────────────────────────
# Tests for _dismiss_cookie_banner
# ──────────────────────────────────────────────────────────────────────
class TestDismissCookieBanner:
    def test_clicks_accept_all_when_present(self):
        """Should click 'Accept All' button if found."""
        page = _mock_page()
        accept_btn = _mock_locator(count=1)
        page.get_by_role = MagicMock(return_value=accept_btn)

        _dismiss_cookie_banner(page)

        accept_btn.first.click.assert_called_once()

    def test_no_error_when_no_banner(self):
        """Should not raise errors when no cookie banner is present."""
        page = _mock_page()
        no_btn = _mock_locator(count=0)
        page.get_by_role = MagicMock(return_value=no_btn)

        # Should not raise
        _dismiss_cookie_banner(page)

    def test_handles_exception_gracefully(self):
        """Should silently handle exceptions."""
        page = _mock_page()
        page.get_by_role = MagicMock(side_effect=Exception("DOM error"))

        # Should not raise
        _dismiss_cookie_banner(page)


# ──────────────────────────────────────────────────────────────────────
# Tests for _safe_text
# ──────────────────────────────────────────────────────────────────────
class TestSafeText:
    def test_returns_text_when_locator_has_elements(self):
        loc = _mock_locator(count=1, text="  Hello World  ")
        assert _safe_text(loc) == "Hello World"

    def test_returns_empty_when_no_elements(self):
        loc = _mock_locator(count=0)
        assert _safe_text(loc) == ""

    def test_returns_empty_on_exception(self):
        loc = MagicMock()
        loc.count = MagicMock(side_effect=Exception("Error"))
        assert _safe_text(loc) == ""


# ──────────────────────────────────────────────────────────────────────
# Tests for _safe_attr
# ──────────────────────────────────────────────────────────────────────
class TestSafeAttr:
    def test_returns_attribute_value(self):
        loc = _mock_locator(count=1, attr_val="https://example.com/page")
        assert _safe_attr(loc, "href") == "https://example.com/page"

    def test_returns_empty_when_no_elements(self):
        loc = _mock_locator(count=0)
        assert _safe_attr(loc, "href") == ""

    def test_returns_empty_when_attr_is_none(self):
        loc = _mock_locator(count=1, attr_val=None)
        assert _safe_attr(loc, "href") == ""

    def test_returns_empty_on_exception(self):
        loc = MagicMock()
        loc.count = MagicMock(side_effect=Exception("Error"))
        assert _safe_attr(loc, "href") == ""


# ──────────────────────────────────────────────────────────────────────
# Tests for _write_record
# ──────────────────────────────────────────────────────────────────────
class TestWriteRecord:
    def test_writes_json_line(self):
        """Should write a valid JSON line to the output file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            tmp_path = f.name

        try:
            data = {"company_name": "Test Co", "booth": "A-101"}
            _write_record(tmp_path, data)

            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            parsed = json.loads(content)
            assert parsed["company_name"] == "Test Co"
            assert parsed["booth"] == "A-101"
        finally:
            os.unlink(tmp_path)

    def test_appends_multiple_records(self):
        """Should append multiple records as separate lines."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            tmp_path = f.name

        try:
            _write_record(tmp_path, {"name": "Company A"})
            _write_record(tmp_path, {"name": "Company B"})
            _write_record(tmp_path, {"name": "Company C"})

            with open(tmp_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]

            assert len(lines) == 3
            assert json.loads(lines[0])["name"] == "Company A"
            assert json.loads(lines[2])["name"] == "Company C"
        finally:
            os.unlink(tmp_path)

    def test_handles_unicode(self):
        """Should correctly handle Japanese/Unicode characters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            tmp_path = f.name

        try:
            data = {"company_name": "株式会社テスト", "booth": "東ホール 1-23"}
            _write_record(tmp_path, data)

            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            parsed = json.loads(content)
            assert parsed["company_name"] == "株式会社テスト"
            assert parsed["booth"] == "東ホール 1-23"
        finally:
            os.unlink(tmp_path)


# ──────────────────────────────────────────────────────────────────────
# Tests for configuration constants
# ──────────────────────────────────────────────────────────────────────
class TestConfig:
    def test_base_url_is_correct(self):
        assert "japan-it.jp" in BASE_URL
        assert "2026" in BASE_URL
        assert "directory" in BASE_URL

    def test_output_file_is_json(self):
        assert OUTPUT_FILE.endswith(".json")
        assert OUTPUT_DETAIL_FILE.endswith(".json")

    def test_output_filenames_contain_japan_it(self):
        assert "japan_it" in OUTPUT_FILE
        assert "japan_it" in OUTPUT_DETAIL_FILE


# ──────────────────────────────────────────────────────────────────────
# Tests for scrape_directory (mocked)
# ──────────────────────────────────────────────────────────────────────
class TestScrapeDirectory:
    def test_opens_browser_and_navigates(self):
        """Should launch browser and navigate to the directory URL."""
        playwright = MagicMock()
        browser = MagicMock()
        context = MagicMock()
        page = _mock_page()

        playwright.chromium.launch = MagicMock(return_value=browser)
        browser.new_context = MagicMock(return_value=context)
        context.new_page = MagicMock(return_value=page)

        # Make locators return 0 to short-circuit the scrape
        page.locator = MagicMock(
            return_value=_mock_locator(count=0)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            scrape_directory(playwright, output_dir=tmpdir)

        page.goto.assert_called_once()
        call_args = page.goto.call_args
        assert BASE_URL in call_args[0][0]

    def test_closes_browser_on_success(self):
        """Should close browser and context after scraping."""
        playwright = MagicMock()
        browser = MagicMock()
        context = MagicMock()
        page = _mock_page()

        playwright.chromium.launch = MagicMock(return_value=browser)
        browser.new_context = MagicMock(return_value=context)
        context.new_page = MagicMock(return_value=page)

        page.locator = MagicMock(
            return_value=_mock_locator(count=0)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            scrape_directory(playwright, output_dir=tmpdir)

        context.close.assert_called_once()
        browser.close.assert_called_once()

    def test_closes_browser_on_error(self):
        """Should close browser even if an error occurs."""
        playwright = MagicMock()
        browser = MagicMock()
        context = MagicMock()
        page = _mock_page()

        playwright.chromium.launch = MagicMock(return_value=browser)
        browser.new_context = MagicMock(return_value=context)
        context.new_page = MagicMock(return_value=page)
        page.goto = MagicMock(side_effect=Exception("Network error"))

        with tempfile.TemporaryDirectory() as tmpdir:
            scrape_directory(playwright, output_dir=tmpdir)

        context.close.assert_called_once()
        browser.close.assert_called_once()


# ──────────────────────────────────────────────────────────────────────
# Tests for scrape_exhibitor_details (mocked)
# ──────────────────────────────────────────────────────────────────────
class TestScrapeExhibitorDetails:
    def test_skips_when_input_file_missing(self, capsys):
        """Should print error and return if input file doesn't exist."""
        playwright = MagicMock()
        scrape_exhibitor_details(playwright, input_file="/nonexistent.json")
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_processes_records_from_input(self):
        """Should visit each exhibitor URL from L1 output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            f.write(json.dumps({"company_name": "Test A",
                                "url": "https://example.com/a"}) + "\n")
            f.write(json.dumps({"company_name": "Test B",
                                "url": "https://example.com/b"}) + "\n")
            tmp_input = f.name

        try:
            playwright = MagicMock()
            browser = MagicMock()
            context = MagicMock()
            page = _mock_page()

            playwright.chromium.launch = MagicMock(return_value=browser)
            browser.new_context = MagicMock(return_value=context)
            context.new_page = MagicMock(return_value=page)

            page.locator = MagicMock(
                return_value=_mock_locator(count=0)
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                scrape_exhibitor_details(
                    playwright,
                    input_file=tmp_input,
                    output_dir=tmpdir,
                )

            # Should have visited both URLs
            assert page.goto.call_count == 2
        finally:
            os.unlink(tmp_input)

    def test_skips_records_without_url(self):
        """Should skip exhibitors that have no URL."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            f.write(json.dumps({"company_name": "No URL Co"}) + "\n")
            f.write(json.dumps({"company_name": "With URL",
                                "url": "https://example.com/x"}) + "\n")
            tmp_input = f.name

        try:
            playwright = MagicMock()
            browser = MagicMock()
            context = MagicMock()
            page = _mock_page()

            playwright.chromium.launch = MagicMock(return_value=browser)
            browser.new_context = MagicMock(return_value=context)
            context.new_page = MagicMock(return_value=page)

            page.locator = MagicMock(
                return_value=_mock_locator(count=0)
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                scrape_exhibitor_details(
                    playwright,
                    input_file=tmp_input,
                    output_dir=tmpdir,
                )

            # Should only visit the one with URL
            assert page.goto.call_count == 1
        finally:
            os.unlink(tmp_input)
