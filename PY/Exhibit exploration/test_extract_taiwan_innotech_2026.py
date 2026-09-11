import importlib.util
import unittest
from pathlib import Path

PATH=Path(__file__).with_name('extract_taiwan_innotech_2026.py')
spec=importlib.util.spec_from_file_location('tie_extractor',PATH);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

CARD='''<li id="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" class=""><h3><label><input name="applyId" value="101" class="exhCK"></label><a href="/en/exhibitor/AAAA/info.html">  Example &amp; Co.  </a></h3><ul><li><span>Brand Name：</span><p> Brand X </p></li><li><span>Products：</span><p>Widgets</p></li><li><span>Physical Show </br>Booth No.:</span><p> Hall 1 <a>B100</a></p></li></ul></li>'''
class ParserTests(unittest.TestCase):
 def test_parses_listing_card(self):
  row=mod.parse_page(CARD,1)[0]
  self.assertEqual(row['exhibitor_id'],'A'*32);self.assertEqual(row['application_id'],'101')
  self.assertEqual(row['company_name'],'Example & Co.');self.assertEqual(row['booth'],'Hall 1 B100')
  self.assertEqual(row['detail_url'],'https://www.inventaipei.com.tw/en/exhibitor/AAAA/info.html')
 def test_rejects_missing_identity(self):
  with self.assertRaises(ValueError):mod.parse_page('<li id="'+('A'*32)+'" class=""><h3></h3></li>',1)
 def test_advertised_total_requires_all_letters(self):
  with self.assertRaises(ValueError):mod.advertised_total('')
if __name__=='__main__':unittest.main()
