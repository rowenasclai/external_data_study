import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from extract_semicon_japan_2026 import ExtractionError, parse_rows, response_rows

ROW = '''<table><tr><td><div data-option-item-id="42"></div></td><td><a href="/exhibitors/exhibitor/42"> 株式会社&nbsp;試験 </a></td><td><a href="https://x/?MapItBooth=A1">Booth</a></td></tr></table>'''
class ParserTests(unittest.TestCase):
    def test_row_normalizes_and_resolves(self):
        row=parse_rows(ROW)[0]
        self.assertEqual(row['exhibitor_id'],'42')
        self.assertEqual(row['company_name'],'株式会社 試験')
        self.assertEqual(row['booth'],'A1')
        self.assertEqual(row['detail_url'],'https://portal2026.semiconjapan.org/exhibitors/exhibitor/42')
    def test_missing_name_fails(self):
        with self.assertRaises(ExtractionError): parse_rows('<tr><div data-option-item-id="2"></div><a href="/co/x"> </a></tr>')
    def test_empty_nonzero_page_fails(self):
        with self.assertRaises(ExtractionError): response_rows({'total': 3, 'data': ''},1)
    def test_missing_total_fails(self):
        with self.assertRaises(ExtractionError): response_rows({'data': ROW},1)
if __name__ == '__main__': unittest.main()
