#!/usr/bin/env python3
"""
Test: Cross-verify SIEMENS RMU data-fields ↔ schema keys ↔ injection pipeline.
Run: python3 test_srmu_injection.py
"""
import sys, os, html as html_module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bs4 import BeautifulSoup
from services.html_template_service import HTMLTemplateService
from models.schemas import SIEMENS_RMU_KEYS, PageData, ExtractedField

# ── Mock OCR data from SRMU.jpeg handwritten values ──
mock_ocr_data = {
    # Header (from SRMU.jpeg)
    "Client": "Desai Kartik",
    "Voltage": "50",
    "Location": "India.",
    "Rating": "8.5",
    "Panel No.": "56",
    "Relay": "60",
    "S/S No.": "6650",
    "SR No.": "60",
    "SWBD": "6530",
    "Type": "Night",
    "Date": "23/03/25",
    "Serviced By": "agent",
    # Checklist (Status + Remarks from SRMU.jpeg)
    "1 Visual inspection of RMU Status": "",
    "1 Visual inspection of RMU Remarks": "",
    "2 Through cleaning of RMU Status": "nice",
    "2 Through cleaning of RMU Remarks": "nice",
    "3 Lubrication of all moving parts Status": "Good",
    "3 Lubrication of all moving parts Remarks": "Good",
    "4 Checking of gear box healthiness Status": "Great",
    "4 Checking of gear box healthiness Remarks": "Great",
    "5 Checking of closing and tripping mechanism Status": "nice",
    "5 Checking of closing and tripping mechanism Remarks": "nice",
    "6 Checking Aux. switch operation Status": "ok",
    "6 Checking Aux. switch operation Remarks": "Ok.",
    "7 Checking of spring charging mechanism Status": "okay",
    "7 Checking of spring charging mechanism Remarks": "okay",
    "8 Checking of closing coil resistance": "nice",
    "8 Remark": "nice",
    "9 Checking of tripping coil resistance": "nice",
    "9 Remark": "nice",
    "10 Checking of spring charging motor resistance": "Good",
    "10 Remark": "Good",
    "11 Checking of all cir clips and lock washers Status": "nice",
    "11 Checking of all cir clips and lock washers Remarks": "okay",
    "12 Checking of power connection tightness Status": "nice",
    "12 Checking of power connection tightness Remarks": "Good",
    "13 Checking ON/OFF operation of RMU Status": "Good",
    "13 Checking ON/OFF operation of RMU Remarks": "nice",
    "14 Spares Replaced/Required Status": "Good",
    "14 Spares Replaced/Required Remarks": "Good",
    "15 After service Of RMU working condition Status": "nice",
    "15 After service Of RMU working condition Remarks": "nice",
    "16 SF6 Gas Pressure Status": "okay",
    "16 SF6 Gas Pressure Remarks": "okay",
    # IR Check (Row 17)
    "IR Check R": "90",
    "IR Check Y": "60",
    "IR Check B": "30",
    "IR Phase to Phase R": "50",
    "IR Phase to Phase Y": "50",
    "IR Phase to Phase B": "25",
    "IR Phase to Earth R": "40",
    "IR Phase to Earth Y": "70",
    "IR Phase to Earth B": "80",
    # CT Table
    "CT R Sr. No.": "1",
    "CT R Ratio": "30",
    "CT R VA": "20",
    "CT R Class": "40",
    "CT R Polarity": "50",
    "CT R Primary Current": "60",
    "CT R Secondary Current": "90",
    "CT R Resistance": "90",
    "CT Y Sr. No.": "2",
    "CT Y Ratio": "50",
    "CT Y VA": "25",
    "CT Y Class": "80",
    "CT Y Polarity": "60",
    "CT Y Primary Current": "80",
    "CT Y Secondary Current": "85",
    "CT Y Resistance": "95",
    "CT B Sr. No.": "3",
    "CT B Ratio": "60",
    "CT B VA": "30",
    "CT B Class": "85",
    "CT B Polarity": "70",
    "CT B Primary Current": "55",
    "CT B Secondary Current": "77",
    "CT B Resistance": "85",
    # Remark
    "Remark": "",
}

# ═══════════════════════════════════════════════════════════
# STEP 1: Schema coverage
# ═══════════════════════════════════════════════════════════
print("=" * 70)
print("STEP 1: Schema key ↔ Mock data coverage")
print("=" * 70)
missing = [k for k in SIEMENS_RMU_KEYS if k not in mock_ocr_data]
extra = [k for k in mock_ocr_data if k not in SIEMENS_RMU_KEYS]
print(f"Schema keys: {len(SIEMENS_RMU_KEYS)}")
print(f"Mock data keys: {len(mock_ocr_data)}")
if missing:
    print(f"✗ MISSING ({len(missing)}):")
    for m in missing:
        print(f"    - '{m}'")
else:
    print("✓ All schema keys covered")
if extra:
    print(f"? EXTRA ({len(extra)}):")
    for e in extra:
        print(f"    - '{e}'")

# ═══════════════════════════════════════════════════════════
# STEP 2: HTML data-field ↔ Schema key match
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 2: HTML data-field ↔ Schema key alignment")
print("=" * 70)

svc = HTMLTemplateService(html_dir="html_pages")
template_path = os.path.join(svc.html_dir, "siemens", "siemens_rmu.html")
with open(template_path, "r", encoding="utf-8") as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, "lxml")
editable = soup.select('[contenteditable="true"]')
df_values = []
for node in editable:
    df = node.get("data-field", "").strip()
    if df:
        df_values.append(html_module.unescape(df))

print(f"Editable cells: {len(editable)}")
print(f"Cells with data-field: {len(df_values)}")
print(f"Cells WITHOUT data-field: {len(editable) - len(df_values)}")

# Check each HTML data-field exists in schema
unmatched = []
for df in df_values:
    if df not in SIEMENS_RMU_KEYS:
        unmatched.append(df)

if unmatched:
    print(f"\n✗ UNMATCHED data-fields ({len(unmatched)}):")
    for u in unmatched:
        print(f"    - '{u}'")
else:
    print("✓ All HTML data-fields match schema keys")

# Check reverse: schema keys not in HTML
html_set = set(df_values)
schema_missing = [k for k in SIEMENS_RMU_KEYS if k not in html_set]
if schema_missing:
    print(f"\n✗ Schema keys missing in HTML ({len(schema_missing)}):")
    for s in schema_missing:
        print(f"    - '{s}'")
else:
    print("✓ All schema keys have matching HTML data-field")

# ═══════════════════════════════════════════════════════════
# STEP 3: Run fill_template_with_data
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 3: Running fill_template_with_data()")
print("=" * 70)

fields = [ExtractedField(key=k, value=v) for k, v in mock_ocr_data.items()]
page = PageData(
    page_number=1,
    title="SIEMENS RMU",
    extracted_fields=fields,
    confidence=0.95,
)
filled_html = svc.fill_template_with_data(
    html_content, [page], document_type="SIEMENS RMU"
)

# ═══════════════════════════════════════════════════════════
# STEP 4: Verify filled cells
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 4: Cell-by-cell verification")
print("=" * 70)

filled_soup = BeautifulSoup(filled_html, "lxml")
filled_nodes = filled_soup.select('[contenteditable="true"]')
ok = 0
bad = 0

for node in filled_nodes:
    df = node.get("data-field", "").strip()
    text = node.get_text(strip=True)
    if df:
        df_u = html_module.unescape(df)
        expected = mock_ocr_data.get(df_u, "")
        if expected == "":
            # Empty expected → should remain empty
            if text == "":
                ok += 1
                # Don't print empty-OK to reduce noise
            else:
                bad += 1
                print(f"  ✗ [{df_u}] got='{text}' but expected EMPTY")
        elif text == expected:
            ok += 1
            print(f"  ✓ [{df_u}] = '{text}'")
        else:
            bad += 1
            print(f"  ✗ [{df_u}] got='{text}' expected='{expected}'")
    else:
        if text:
            bad += 1
            print(f"  ? [NO data-field] got='{text}' (unexpected fill)")

print(f"\n  RESULT: {ok} OK, {bad} FAILED")

# ═══════════════════════════════════════════════════════════
# STEP 5: Save output
# ═══════════════════════════════════════════════════════════
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output_srmu.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(filled_html)

print(f"\n{'='*70}")
print(f"Output saved: {output_path}")
print(f"Open: google-chrome --no-sandbox {output_path}")
print(f"{'='*70}")
