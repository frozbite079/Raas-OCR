#!/usr/bin/env python3
"""
Test script: Simulates OCR injection into HT Panel Preventive Maintenance template.
Creates a filled HTML output and opens it in Chrome for visual verification.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.html_template_service import HTMLTemplateService
from models.schemas import HT_PANEL_PM_CHECKLIST_KEYS, DOCUMENT_TYPE_KEYS

# ── Build mock OCR data matching real handwritten values from HTPANEL1.pdf ──
mock_ocr_data = {
    # Header
    "Customer": "Rahul Roy",
    "Board No": "55",
    "Sub Station": "Main SS",
    "Date": "23/03/26",
    "Number Of Vertical": "4",
    "Number Of VCB": "3",
    # Bus bar Chamber (A-1 to A-4)
    "A-1 Bus bar Chamber cleaning inspection": "Rahul Roy",
    "A-1 Remark": "55",
    "A-2 Check for presence of joint shrouds": "okay",
    "A-2 Remark": "okay",
    "A-3 Checking for opening and foreign particle": "indi.",
    "A-3 Remark": "23/03/26",
    "A-4 Proper closing of Internal arc flaps & box up": "okay",
    "A-4 Remark": "okay",
    # VCB chamber (B-1 to B-8)
    "B-1 VCB Chamber cleaning": "okay",
    "B-1 Remark": "okay",
    "B-2 Check Safety shutter movement": "60",
    "B-2 Remark": "55",
    "B-3 Check VCB Racking in/out": "Good",
    "B-3 Remark": "Good",
    "B-4 Greasing of racking screw": "Great",
    "B-4 Remark": "okay",
    "B-5 Greasing of PDS contact": "nice",
    "B-5 Remark": "nice",
    "B-6 Check for SDS alignment": "good",
    "B-6 Remark": "good",
    "B-7 Limit switch operation": "nice",
    "B-7 Remark": "nice",
    "B-8 Ensure all unused holes are blocked": "good",
    "B-8 Remark": "good",
    # LV chamber (C-1, C-2)
    "C-1 LV Chamber cleaning & verification": "okay",
    "C-1 Remark": "nice",
    "C-2 Proper lug crimping": "Good",
    "C-2 Remark": "okay",
    # Cable chamber (D-1 to D-5)
    "D-1 Cable chamber cleaning": "better",
    "D-1 Remark": "better",
    "D-2 PDS to link hardware tightness": "okay",
    "D-2 Remark": "nice",
    "D-3 Checking healthiness of Space heater": "okay",
    "D-3 Remark": "Good",
    "D-4 Presence of rear door fixing hardware": "nice",
    "D-4 Remark": "nice",
    "D-5 Ensure all unused holes are blocked": "good",
    "D-5 Remark": "good",
    # Line & Bus PT trolley (E-1, E-2)
    "E-1 Free movement from Test and Service position": "perfect",
    "E-1 Remark": "perfect",
    "E-2 Proper contact pressure and alignment": "Good",
    "E-2 Remark": "okay",
    # Mechanical operation (F-1)
    "F-1 Ensure mechanical ON/OFF operation": "nice",
    "F-1 Remark": "nice",
    # Electrical Operation (G-1)
    "G-1 Incomer Bus-coupler operation as per scheme": "good",
    "G-1 Remark": "good",
    # Contact Resistance Test (H-1)
    "H-1 Contact resistance of main bus bar": "perfect",
    "H-1 Remark": "perfect",
    "H-1 Contact resistance of VCBs": "perfect",
    "H-1 VCBs Remark": "perfect",
    # PM Before IR Test (1.0)
    "PM Before R-E": "60",
    "PM Before Y-E": "50",
    "PM Before B-E": "80",
    "PM Before N-E": "30",
    "PM Before R-Y": "45",
    "PM Before Y-B": "55",
    "PM Before B-R": "65",
    # PM After IR Test (2.0)
    "PM After R-E": "70",
    "PM After Y-E": "70",
    "PM After B-E": "80",
    "PM After N-E": "100",
    "PM After R-Y": "75",
    "PM After Y-B": "85",
    "PM After B-R": "90",
}

# ── Step 1: Verify all schema keys have a mock value ──
print("=" * 70)
print("STEP 1: Schema key coverage check")
print("=" * 70)
missing = [k for k in HT_PANEL_PM_CHECKLIST_KEYS if k not in mock_ocr_data]
extra = [k for k in mock_ocr_data if k not in HT_PANEL_PM_CHECKLIST_KEYS]
print(f"Schema keys: {len(HT_PANEL_PM_CHECKLIST_KEYS)}")
print(f"Mock data keys: {len(mock_ocr_data)}")
if missing:
    print(f"MISSING ({len(missing)} keys not in mock):")
    for m in missing:
        print(f"  ✗ {m}")
else:
    print("✓ All schema keys have mock values")
if extra:
    print(f"EXTRA ({len(extra)} keys not in schema):")
    for e in extra:
        print(f"  ? {e}")

# ── Step 2: Verify HTML template has matching data-field attributes ──
print("\n" + "=" * 70)
print("STEP 2: HTML data-field vs schema key match")
print("=" * 70)

import html as html_module
from bs4 import BeautifulSoup

svc = HTMLTemplateService(html_dir="html_pages")
template_path = os.path.join(svc.html_dir, "ht_panel_preventive_maintenance.html")
with open(template_path, "r", encoding="utf-8") as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, "lxml")
editable_nodes = soup.select('[contenteditable="true"]')
data_field_values = []
for node in editable_nodes:
    df = node.get("data-field", "").strip()
    if df:
        data_field_values.append(html_module.unescape(df))

print(f"Editable cells in template: {len(editable_nodes)}")
print(f"Cells with data-field: {len(data_field_values)}")
print(f"Cells without data-field: {len(editable_nodes) - len(data_field_values)}")

# Check each data-field against schema
unmatched_df = []
for df in data_field_values:
    if df not in HT_PANEL_PM_CHECKLIST_KEYS:
        # Try case-insensitive
        found = any(k.lower() == df.lower() for k in HT_PANEL_PM_CHECKLIST_KEYS)
        if not found:
            unmatched_df.append(df)

if unmatched_df:
    print(f"\nUNMATCHED data-fields ({len(unmatched_df)}):")
    for u in unmatched_df:
        print(f"  ✗ '{u}'")
else:
    print("✓ All data-field values match schema keys")

# ── Step 3: Run the actual injection ──
print("\n" + "=" * 70)
print("STEP 3: Running fill_template_with_data()")
print("=" * 70)

from models.schemas import PageData, ExtractedField

fields = [ExtractedField(key=k, value=v) for k, v in mock_ocr_data.items()]
page = PageData(
    page_number=1,
    title="HT PANEL PREVENTIVE MAINTENANCE CHECKLIST",
    extracted_fields=fields,
    confidence=0.95,
)

filled_html = svc.fill_template_with_data(
    html_content, [page], document_type="HT PANEL PREVENTIVE MAINTENANCE CHECKLIST"
)

# ── Step 4: Verify filled output ──
print("\n" + "=" * 70)
print("STEP 4: Verifying filled output")
print("=" * 70)

filled_soup = BeautifulSoup(filled_html, "lxml")
filled_nodes = filled_soup.select('[contenteditable="true"]')
filled_count = 0
empty_count = 0
alignment_report = []

for node in filled_nodes:
    df = node.get("data-field", "").strip()
    text = node.get_text(strip=True)
    if df:
        df_unescaped = html_module.unescape(df)
        expected = mock_ocr_data.get(df_unescaped, "")
        if text:
            filled_count += 1
            status = "✓" if text == expected else f"✗ expected='{expected}'"
            alignment_report.append(f"  {status} [{df_unescaped}] = '{text}'")
        else:
            empty_count += 1
            alignment_report.append(f"  ✗ EMPTY [{df_unescaped}] (expected='{expected}')")
    else:
        if text:
            filled_count += 1
            alignment_report.append(f"  ? (no data-field) = '{text}'")
        else:
            empty_count += 1

print(f"Filled cells: {filled_count}")
print(f"Empty cells: {empty_count}")
print(f"\nAlignment details:")
for line in alignment_report:
    print(line)

# ── Step 5: Save output ──
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output_ht_panel.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(filled_html)

print(f"\n{'='*70}")
print(f"Output saved to: {output_path}")
print(f"Open in Chrome: google-chrome --no-sandbox {output_path}")
print(f"{'='*70}")
