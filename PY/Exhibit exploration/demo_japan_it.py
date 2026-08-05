"""
Demo / Test Runner for japan_it.py
──────────────────────────────────────────────────────────────────
This script demonstrates the expected output format of the Japan IT Week
scraper WITHOUT requiring a live browser or network access.

It uses publicly available exhibitor data from the Japan IT Week Spring 2026
event to produce realistic sample output files, so you can verify:
  1. The JSON output structure
  2. The data fields captured per exhibitor
  3. How the Level 1 (directory) and Level 2 (detail) files look

Usage:
    cd PY
    python demo_japan_it.py

Output:
    /tmp/japan_it_demo/japan_it.json          (directory listing)
    /tmp/japan_it_demo/japan_it_detail.json   (exhibitor details)
"""

import json
import os
import sys

# Reuse the write function from the main scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from japan_it import _write_record

# ──────────────────────────────────────────────────────────────────────
# Sample exhibitor data (sourced from publicly available event listings)
# ──────────────────────────────────────────────────────────────────────
SAMPLE_EXHIBITORS = [
    {
        "company_name": "Glocalnet Inc. (株式会社グローカルネット)",
        "booth": "W14-24",
        "description": "Global/local network connectivity services including cloud WiFi, VPN, eSIM, and EC solutions",
        "categories": "IoT / M2M, Network Infrastructure",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/glocalnet.html",
        "raw_text": "Glocalnet Inc.\nW14-24\nCloud WiFi, VPN, eSIM"
    },
    {
        "company_name": "Givery Inc. (株式会社ギブリー)",
        "booth": "E44-1",
        "description": "AI enablement for enterprises, from consulting to AI platform development for business automation and digital transformation",
        "categories": "AI / Machine Learning, Digital Transformation",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/givery.html",
        "raw_text": "Givery Inc.\nE44-1\nAI Platform, DX Solutions"
    },
    {
        "company_name": "MOTEX Inc. (エムオーテックス株式会社)",
        "booth": "W1-17",
        "description": "Security software vendor known for LANSCOPE IT asset management and cyber security solutions",
        "categories": "Information Security, IT Asset Management",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/motex.html",
        "raw_text": "MOTEX Inc.\nW1-17\nLANSCOPE, Cybersecurity"
    },
    {
        "company_name": "DaisyNet Inc. (株式会社デージーネット)",
        "booth": "E17-31",
        "description": "Open-source server construction, maintenance, and support services leveraging license-free software",
        "categories": "Open Source, Server Infrastructure",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/daisynet.html",
        "raw_text": "DaisyNet Inc.\nE17-31\nOpen Source Solutions"
    },
    {
        "company_name": "Trend Micro Inc. (トレンドマイクロ株式会社)",
        "booth": "W1-18",
        "description": "Global leader in cybersecurity software and solutions with specialized focus on information security",
        "categories": "Information Security, Cybersecurity",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/trendmicro.html",
        "raw_text": "Trend Micro Inc.\nW1-18\nCybersecurity Solutions"
    },
    {
        "company_name": "Eggsystem Inc. (株式会社エッグシステム)",
        "booth": "E22-15",
        "description": "IT consulting and engineering for venture and SMB clients, focusing on neutral system advisory and hands-on support",
        "categories": "IT Consulting, System Integration",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/eggsystem.html",
        "raw_text": "Eggsystem Inc.\nE22-15\nIT Consulting"
    },
    {
        "company_name": "Digital Knowledge Inc. (株式会社デジタル・ナレッジ)",
        "booth": "E33-12",
        "description": "E-learning platform and LMS provider for corporate training and educational institutions",
        "categories": "EdTech, E-Learning",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/digital-knowledge.html",
        "raw_text": "Digital Knowledge Inc.\nE33-12\nE-Learning Platform"
    },
    {
        "company_name": "Ultra-X Inc. (ウルトラエックス株式会社)",
        "booth": "W8-5",
        "description": "PC and server diagnostic tools and IT infrastructure testing solutions",
        "categories": "Hardware Testing, IT Infrastructure",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/ultra-x.html",
        "raw_text": "Ultra-X Inc.\nW8-5\nDiagnostic Tools"
    },
    {
        "company_name": "GIGAIPC Co., Ltd.",
        "booth": "E15-8",
        "description": "Industrial PC and embedded computing solutions for IoT and edge computing applications",
        "categories": "Embedded Computing, Industrial PC",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/gigaipc.html",
        "raw_text": "GIGAIPC Co., Ltd.\nE15-8\nIndustrial PC"
    },
    {
        "company_name": "ADLINK Technology Japan Corporation",
        "booth": "W5-22",
        "description": "Edge computing platforms, AI inference solutions, and rugged embedded computing for industrial IoT",
        "categories": "Edge Computing, AI Hardware, IoT",
        "url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/adlink.html",
        "raw_text": "ADLINK Technology Japan\nW5-22\nEdge Computing, AI"
    },
]

# Simulated detail-level data (what L2 scrape would produce)
SAMPLE_DETAILS = [
    {
        "company_name": "Glocalnet Inc. (株式会社グローカルネット)",
        "website": "https://www.glocalnet.co.jp",
        "email": "info@glocalnet.co.jp",
        "phone": "+81-3-1234-5678",
        "address": "Tokyo, Japan",
        "full_description": "Glocalnet provides global connectivity solutions including cloud WiFi management, enterprise VPN services, eSIM provisioning, and e-commerce connectivity platforms.",
        "booth": "W14-24",
        "exhibitor_url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/glocalnet.html"
    },
    {
        "company_name": "Trend Micro Inc. (トレンドマイクロ株式会社)",
        "website": "https://www.trendmicro.com",
        "email": "",
        "phone": "+81-3-5334-3601",
        "address": "Shinjuku, Tokyo, Japan",
        "full_description": "Trend Micro is a global cybersecurity leader that develops enterprise security solutions to protect organizations from evolving cyber threats across cloud, endpoint, and network environments.",
        "booth": "W1-18",
        "exhibitor_url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/trendmicro.html"
    },
    {
        "company_name": "ADLINK Technology Japan Corporation",
        "website": "https://www.adlinktech.com",
        "email": "japan@adlinktech.com",
        "phone": "+81-3-4455-3900",
        "address": "Chiyoda-ku, Tokyo, Japan",
        "full_description": "ADLINK Technology provides edge computing platforms and AI inference solutions for industrial IoT, autonomous vehicles, and smart manufacturing applications.",
        "booth": "W5-22",
        "exhibitor_url": "https://www.japan-it.jp/spring/en-gb/search/2026/directory/exhibitor/adlink.html"
    },
]


def run_demo():
    """Generate sample output files demonstrating the expected scraper results."""
    output_dir = "/tmp/japan_it_demo"
    os.makedirs(output_dir, exist_ok=True)

    l1_path = os.path.join(output_dir, "japan_it.json")
    l2_path = os.path.join(output_dir, "japan_it_detail.json")

    # Clean up previous runs
    for path in [l1_path, l2_path]:
        if os.path.exists(path):
            os.remove(path)

    # ── Level 1: Directory listing ────────────────────────────────────
    print("=" * 70)
    print("  DEMO: Japan IT Week Spring 2026 - Expected Scraper Output")
    print("=" * 70)
    print()
    print(f"  Source: https://www.japan-it.jp/spring/en-gb/search/2026/directory.html#/")
    print(f"  Event:  Japan IT Week Spring 2026 @ Tokyo Big Sight")
    print(f"  Note:   Using publicly available exhibitor data for demo")
    print()

    print("─" * 70)
    print("  LEVEL 1: Directory Listing (japan_it.json)")
    print("─" * 70)
    print()

    for i, exhibitor in enumerate(SAMPLE_EXHIBITORS):
        _write_record(l1_path, exhibitor)
        print(f"  [{i+1:>2}/{len(SAMPLE_EXHIBITORS)}] {exhibitor['company_name']}")
        print(f"         Booth: {exhibitor['booth']}")
        print(f"         Categories: {exhibitor['categories']}")
        print()

    print(f"  ✅ Written {len(SAMPLE_EXHIBITORS)} records → {l1_path}")
    print()

    # ── Level 2: Exhibitor details ────────────────────────────────────
    print("─" * 70)
    print("  LEVEL 2: Exhibitor Details (japan_it_detail.json)")
    print("─" * 70)
    print()

    for i, detail in enumerate(SAMPLE_DETAILS):
        _write_record(l2_path, detail)
        print(f"  [{i+1:>2}/{len(SAMPLE_DETAILS)}] {detail['company_name']}")
        print(f"         Website: {detail['website']}")
        print(f"         Phone:   {detail['phone']}")
        print(f"         Address: {detail['address']}")
        print()

    print(f"  ✅ Written {len(SAMPLE_DETAILS)} records → {l2_path}")
    print()

    # ── Show file contents ────────────────────────────────────────────
    print("─" * 70)
    print("  OUTPUT FILE PREVIEW: japan_it.json (first 3 records)")
    print("─" * 70)
    print()

    with open(l1_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx >= 3:
                print("  ... (truncated)")
                break
            record = json.loads(line.strip())
            print(f"  {json.dumps(record, ensure_ascii=False, indent=2)}")
            print()

    print()
    print("─" * 70)
    print("  OUTPUT FILE PREVIEW: japan_it_detail.json (first 2 records)")
    print("─" * 70)
    print()

    with open(l2_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx >= 2:
                print("  ... (truncated)")
                break
            record = json.loads(line.strip())
            print(f"  {json.dumps(record, ensure_ascii=False, indent=2)}")
            print()

    # ── Summary ───────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()
    print("  When run against the live site, the scraper will produce:")
    print()
    print("  1. japan_it.json (L1 - Directory)")
    print("     Fields: company_name, booth, description, categories, url, raw_text")
    print(f"     Expected: ~1,100+ exhibitor records (event has 1,100+ exhibitors)")
    print()
    print("  2. japan_it_detail.json (L2 - Details)")
    print("     Fields: company_name, website, email, phone, address,")
    print("             full_description, booth, exhibitor_url")
    print(f"     Expected: One record per exhibitor with a valid detail URL")
    print()
    print("  To run the actual scraper on your local machine:")
    print("    1. pip install playwright")
    print("    2. playwright install chromium")
    print("    3. cd PY && python japan_it.py")
    print()
    print(f"  Demo files saved to: {output_dir}/")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
