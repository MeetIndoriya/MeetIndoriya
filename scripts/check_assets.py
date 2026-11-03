#!/usr/bin/env python3
"""Fail the workflow (and keep the old assets live) if anything generated would break on GitHub."""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_KB, MAX_TOTAL_KB = 200, 450
errors, total = [], 0

for f in sorted((ROOT / "assets").rglob("*.svg")):
    s = f.read_text(encoding="utf-8")
    kb = len(s.encode()) / 1024
    total += kb
    try:
        ET.fromstring(s)
    except ET.ParseError as e:
        errors.append(f"{f.name}: invalid XML ({e})")
        continue
    low = s.lower()
    for bad in ("<script", "<foreignobject", "javascript:", " onload=", " onclick="):
        if bad in low:
            errors.append(f"{f.name}: forbidden construct {bad.strip()}")
    for m in re.finditer(r'(?:href|src)="([^"#][^"]*)"', s):
        if not m.group(1).startswith("data:"):
            errors.append(f"{f.name}: external reference {m.group(1)[:50]} (GitHub blocks these inside <img>)")
    if "viewBox" not in s:
        errors.append(f"{f.name}: missing viewBox (not responsive)")
    if kb > MAX_KB:
        errors.append(f"{f.name}: {kb:.0f} KB exceeds {MAX_KB} KB budget")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
for src in re.findall(r'src="(assets/[^"]+)"', readme):
    if not (ROOT / src).exists():
        errors.append(f"README references missing file {src}")
for img in re.findall(r"<img[^>]*>", readme):
    if 'alt="' not in img or 'alt=""' in img:
        errors.append(f"README image without alt text: {img[:70]}")
    if 'width="100%"' not in img:
        errors.append(f"README image not responsive: {img[:70]}")
if total > MAX_TOTAL_KB:
    errors.append(f"total asset size {total:.0f} KB exceeds {MAX_TOTAL_KB} KB")

print(f"checked {len(list((ROOT/'assets').rglob('*.svg')))} SVGs, {total:.0f} KB total")
if errors:
    print("\n".join("FAIL " + e for e in errors))
    sys.exit(1)
print("all checks passed")
