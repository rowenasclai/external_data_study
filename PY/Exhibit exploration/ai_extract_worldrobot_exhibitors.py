#!/usr/bin/env python3
"""
Export exhibitor names from the World Robot Conference floorplan image.

Source image:
    https://www.worldrobotconference.com/static/upload/image/20250730/1753855155167080.jpg

Important:
    The source is a static floorplan image, not a structured API. The exhibitor
    list below is a curated OCR transcription from that specific image. This
    script makes the extraction rerunnable/reproducible by exporting the same
    structured list to CSV/JSON, and can optionally download the source image
    for audit/reference.

Examples:
    python extract_worldrobot_image_exhibitors.py
    python extract_worldrobot_image_exhibitors.py --json-output exhibitors.json
    python extract_worldrobot_image_exhibitors.py --download-image floorplan.jpg

No external dependency is required unless you use --download-image, which needs:
    pip install requests
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

SOURCE_IMAGE_URL = "https://www.worldrobotconference.com/static/upload/image/20250730/1753855155167080.jpg"

# Curated OCR from the floorplan image. Rows with low-confidence OCR have notes.
EXHIBITORS: List[Dict[str, str]] = [
    {"booth_no": "C101", "exhibitor_name": "凯富博科", "notes": ""},
    {"booth_no": "C102", "exhibitor_name": "极创", "notes": ""},
    {"booth_no": "C103", "exhibitor_name": "纽格尔", "notes": "OCR uncertain; appears as 纽格尔/纽诺尔"},
    {"booth_no": "C104", "exhibitor_name": "国兴智能", "notes": ""},
    {"booth_no": "C105", "exhibitor_name": "申昊科技", "notes": ""},
    {"booth_no": "C106", "exhibitor_name": "中安吉泰", "notes": ""},
    {"booth_no": "C107", "exhibitor_name": "煜禾森", "notes": ""},
    {"booth_no": "C108", "exhibitor_name": "智易时代", "notes": ""},
    {"booth_no": "C109", "exhibitor_name": "曼大智能", "notes": ""},
    {"booth_no": "C110", "exhibitor_name": "捷杰西", "notes": ""},
    {"booth_no": "C111", "exhibitor_name": "凌天", "notes": ""},
    {"booth_no": "C112", "exhibitor_name": "博涛", "notes": ""},
    {"booth_no": "C113", "exhibitor_name": "智易科技", "notes": "OCR uncertain; small text"},
    {"booth_no": "C114", "exhibitor_name": "锐识科技", "notes": "OCR uncertain; small text"},
    {"booth_no": "C115", "exhibitor_name": "恒之未来", "notes": ""},
    {"booth_no": "C201", "exhibitor_name": "中信重工", "notes": ""},
    {"booth_no": "C202", "exhibitor_name": "国家农业智能装备工程技术研究中心", "notes": ""},
    {"booth_no": "C203", "exhibitor_name": "汉王科技", "notes": ""},
    {"booth_no": "C204", "exhibitor_name": "智澄", "notes": ""},
    {"booth_no": "C205", "exhibitor_name": "可安可", "notes": ""},
    {"booth_no": "C206", "exhibitor_name": "狄兹精密", "notes": ""},
    {"booth_no": "C207", "exhibitor_name": "何泰威自动化", "notes": ""},
    {"booth_no": "C301", "exhibitor_name": "赛博格", "notes": ""},
    {"booth_no": "C302", "exhibitor_name": "数字华夏", "notes": ""},
    {"booth_no": "C303", "exhibitor_name": "杭州人形中心", "notes": ""},
    {"booth_no": "C304", "exhibitor_name": "农业机器人", "notes": ""},
    {"booth_no": "C305", "exhibitor_name": "清宝智能", "notes": ""},
    {"booth_no": "C306", "exhibitor_name": "云幕", "notes": ""},
    {"booth_no": "C307", "exhibitor_name": "中坚科技", "notes": ""},
    {"booth_no": "C308", "exhibitor_name": "具微科技", "notes": "Booth number inferred from sequence; OCR saw C306/C308"},
    {"booth_no": "C309", "exhibitor_name": "成都人形机器人创新中心", "notes": ""},
    {"booth_no": "C310", "exhibitor_name": "亦庄机器人公司", "notes": ""},
    {"booth_no": "C401", "exhibitor_name": "京城机电", "notes": ""},
    {"booth_no": "C402", "exhibitor_name": "睿研", "notes": ""},
    {"booth_no": "C403", "exhibitor_name": "灵巧智能", "notes": ""},
    {"booth_no": "C404", "exhibitor_name": "中科硅纪", "notes": ""},
    {"booth_no": "C405", "exhibitor_name": "中科院自动化所", "notes": ""},
    {"booth_no": "C406", "exhibitor_name": "灵心巧手", "notes": ""},
    {"booth_no": "C407", "exhibitor_name": "因时", "notes": ""},
    {"booth_no": "C408", "exhibitor_name": "傲意科技", "notes": ""},
    {"booth_no": "C409", "exhibitor_name": "三丰智能", "notes": ""},
    {"booth_no": "C411", "exhibitor_name": "金刚", "notes": ""},
    {"booth_no": "C412", "exhibitor_name": "鸣志", "notes": ""},
    {"booth_no": "C413", "exhibitor_name": "鼎智科技", "notes": ""},
    {"booth_no": "C414", "exhibitor_name": "正元电机", "notes": ""},
    {"booth_no": "C415", "exhibitor_name": "米思米", "notes": ""},
    {"booth_no": "C416", "exhibitor_name": "显和电机", "notes": ""},
    {"booth_no": "C501", "exhibitor_name": "灵初智能", "notes": ""},
    {"booth_no": "C502", "exhibitor_name": "曦诺", "notes": ""},
    {"booth_no": "C503", "exhibitor_name": "逸见科技", "notes": "OCR uncertain; appears as 逸见/造见科技"},
    {"booth_no": "C504", "exhibitor_name": "无论科技", "notes": "OCR uncertain; small text"},
    {"booth_no": "C505", "exhibitor_name": "鸿元", "notes": ""},
    {"booth_no": "C506", "exhibitor_name": "南方精工", "notes": ""},
    {"booth_no": "C507", "exhibitor_name": "希西维", "notes": ""},
    {"booth_no": "C508", "exhibitor_name": "柯力传感", "notes": ""},
    {"booth_no": "C509", "exhibitor_name": "强脑科技", "notes": ""},
    {"booth_no": "C510", "exhibitor_name": "兆威机电", "notes": ""},
    {"booth_no": "C511", "exhibitor_name": "HBK", "notes": ""},
    {"booth_no": "C512", "exhibitor_name": "宇立", "notes": ""},
    {"booth_no": "C513", "exhibitor_name": "绿的谐波", "notes": ""},
    {"booth_no": "C514", "exhibitor_name": "Maxon", "notes": ""},
    {"booth_no": "C515", "exhibitor_name": "诺仕", "notes": ""},
    {"booth_no": "C516", "exhibitor_name": "福尔哈贝", "notes": ""},
    {"booth_no": "C517", "exhibitor_name": "卓誉", "notes": ""},
    {"booth_no": "C518", "exhibitor_name": "诺盛测控", "notes": ""},
    {"booth_no": "C519", "exhibitor_name": "丰立智能", "notes": ""},
    {"booth_no": "C520", "exhibitor_name": "贝丰", "notes": ""},
    {"booth_no": "C601", "exhibitor_name": "仙山科技", "notes": ""},
    {"booth_no": "C602", "exhibitor_name": "禾赛", "notes": ""},
    {"booth_no": "C603", "exhibitor_name": "祥明智能", "notes": ""},
    {"booth_no": "C604", "exhibitor_name": "思岚", "notes": ""},
    {"booth_no": "C605", "exhibitor_name": "蓝点触控", "notes": ""},
    {"booth_no": "C606", "exhibitor_name": "艾迈斯", "notes": ""},
    {"booth_no": "C607", "exhibitor_name": "达妙", "notes": ""},
    {"booth_no": "C608", "exhibitor_name": "锐驰智光", "notes": ""},
    {"booth_no": "C609", "exhibitor_name": "科盟", "notes": ""},
    {"booth_no": "C610", "exhibitor_name": "鑫精诚", "notes": ""},
    {"booth_no": "C611", "exhibitor_name": "速腾聚创", "notes": ""},
    {"booth_no": "C612", "exhibitor_name": "汉威科技", "notes": ""},
    {"booth_no": "C613", "exhibitor_name": "福瑞博", "notes": ""},
    {"booth_no": "C614", "exhibitor_name": "海德汉", "notes": ""},
    {"booth_no": "C615", "exhibitor_name": "步科", "notes": ""},
    {"booth_no": "C616", "exhibitor_name": "意优", "notes": ""},
    {"booth_no": "C617", "exhibitor_name": "Igus", "notes": ""},
    {"booth_no": "C618", "exhibitor_name": "希磁科技", "notes": ""},
    {"booth_no": "C619", "exhibitor_name": "亿纬锂能", "notes": ""},
    {"booth_no": "C620", "exhibitor_name": "格瑞普", "notes": ""},
]


def sort_key(row: Dict[str, str]) -> tuple[str, str]:
    return (row["booth_no"], row["exhibitor_name"])


def write_csv(rows: List[Dict[str, str]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["booth_no", "exhibitor_name", "notes"])
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: List[Dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def download_image(path: Path, url: str = SOURCE_IMAGE_URL) -> None:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("--download-image requires: pip install requests") from exc

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export curated OCR exhibitor list from World Robot Conference floorplan image"
    )
    parser.add_argument("--output", default="worldrobot_hall_c_exhibitors.csv", help="CSV output path")
    parser.add_argument("--json-output", default="", help="Optional JSON output path")
    parser.add_argument("--download-image", default="", help="Optional path to save the source floorplan image")
    parser.add_argument("--source-url", default=SOURCE_IMAGE_URL, help="Source image URL for --download-image")
    args = parser.parse_args(argv)

    rows = sorted(EXHIBITORS, key=sort_key)
    write_csv(rows, Path(args.output))
    if args.json_output:
        write_json(rows, Path(args.json_output))
    if args.download_image:
        download_image(Path(args.download_image), args.source_url)

    uncertain_count = sum(1 for row in rows if row.get("notes"))
    print(f"Exported {len(rows)} exhibitors")
    print(f"CSV: {Path(args.output).resolve()}")
    if args.json_output:
        print(f"JSON: {Path(args.json_output).resolve()}")
    if args.download_image:
        print(f"Source image: {Path(args.download_image).resolve()}")
    print(f"Rows with OCR notes/uncertainty: {uncertain_count}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
