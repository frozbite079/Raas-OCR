"""
Test script to verify OCR extraction for SERVICE REPORT FOR LV CIRCUIT BREAKER
against the actual SR.pdf values.

Run: python test_sr_lv_ocr.py
"""
import os
import sys
import json

# Add project root to path
sys.path.insert(0, "/home/redspark/Pictures/Raas-OCR")
os.chdir("/home/redspark/Pictures/Raas-OCR")

from dotenv import load_dotenv
load_dotenv()

from services.html_template_service import HTMLTemplateService
from models.schemas import (
    PageData, ExtractedField,
    SERVICE_REPORT_LV_CIRCUIT_BREAKER_KEYS
)

# ── Expected values from SR.pdf (manually read from image) ─────────────────
EXPECTED = {
    # Header
    "Client":               "ravi patel",
    "Tested On":            "21/03/26",
    "Plant":                "india",
    "Tested By":            "rahul",
    "SWBD":                 "well111",
    "Feeder":               "barodian",
    # 1.0 Breaker Details
    "Make":                 "111",
    "Breaker Serial No.":   "F560F11",
    "Rated Voltage":        "50V",
    "Rated Current":        "60",
    "Breaking Capacity":    "50",
    "Type of Breaker":      "long",
    # 1.7 Release Details  ← new keys matching HTML data-field
    "1.7 Release Type":     "ETU45B",
    "1.7 LT":               "60",
    "1.7 tR Sec IR":        "10",
    "1.7 ST":               "70",
    "1.7 Tsd":              "80",
    "1.7 I Inst":           "50",
    "1.7 CT Ohm":           "88",
    "1.7 GF":               "59",
    "1.7 Tg":               "66",
    # 1.8 Resistance  ← new keys matching HTML data-field
    "1.8 UV Value":         "45",
    "1.8 UV Voltage":       "34",
    "1.8 Motor Value":      "34",
    "1.8 Motor Voltage":    "220V AC/DC",
    "1.8 CC Value":         "45",
    "1.8 CC Voltage":       "34",
    "1.8 TC Value":         "23",
    "1.8 TC Voltage":       "220V AC/DC",
}

# ── STEP 1: Check schema keys vs HTML data-fields ─────────────────────────
print("\n" + "="*70)
print("STEP 1: SCHEMA KEYS vs HTML data-field AUDIT")
print("="*70)

svc = HTMLTemplateService()
html_content = svc.load_template("siemens/service_report_for_lv_circuit_breaker.html")
if not html_content:
    # try the non-siemens path
    html_content = svc.load_template("service_report_lv_circuit_breaker.html")

if html_content:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Collect all data-field values from the HTML
    html_fields = set()
    for node in soup.find_all(attrs={"data-field": True}):
        html_fields.add(node["data-field"])
    
    print(f"\nTotal data-field attributes in HTML: {len(html_fields)}")
    print(f"Total keys in schema: {len(SERVICE_REPORT_LV_CIRCUIT_BREAKER_KEYS)}")
    
    # Schema keys NOT in HTML
    schema_not_in_html = []
    for key in SERVICE_REPORT_LV_CIRCUIT_BREAKER_KEYS:
        # Normalize comparison
        if key not in html_fields:
            schema_not_in_html.append(key)
    
    # HTML fields NOT in schema
    html_not_in_schema = []
    for field in html_fields:
        if field not in SERVICE_REPORT_LV_CIRCUIT_BREAKER_KEYS:
            html_not_in_schema.append(field)
    
    print(f"\n❌ Schema keys MISSING from HTML data-field attributes ({len(schema_not_in_html)}):")
    for k in schema_not_in_html:
        print(f"   - '{k}'")
    
    print(f"\n⚠️  HTML data-field attributes NOT in schema ({len(html_not_in_schema)}):")
    for k in sorted(html_not_in_schema):
        print(f"   - '{k}'")
    
    # Show all HTML fields for reference
    print(f"\n📋 All HTML data-field attributes found:")
    for f in sorted(html_fields):
        print(f"   '{f}'")
else:
    print("❌ Could not load HTML template!")

# ── STEP 2: Run actual OCR on the PDF ────────────────────────────────────
print("\n" + "="*70)
print("STEP 2: RUNNING ACTUAL OCR ON SR.pdf")
print("="*70)

pdf_path = "/home/redspark/Pictures/Raas-OCR/new_tsting_SI/SR.pdf"
if not os.path.exists(pdf_path):
    print(f"❌ PDF not found at {pdf_path}")
    sys.exit(1)

print(f"📄 Processing: {pdf_path}")

import asyncio
from services.ocr_service import OCRService
from fastapi import UploadFile
import io

async def run_ocr():
    ocr = OCRService()
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    # Simulate UploadFile
    class FakeUpload:
        filename = "SR.pdf"
        async def read(self):
            return pdf_bytes
    
    result = await ocr.process_documents(
        files=[FakeUpload()],
        document_type="SERVICE REPORT FOR LV CIRCUIT BREAKER",
        include_html=True,
    )
    return result

result = asyncio.run(run_ocr())

# ── STEP 3: Compare OCR output vs expected ────────────────────────────────
print("\n" + "="*70)
print("STEP 3: OCR EXTRACTED VALUES vs EXPECTED (from PDF image)")
print("="*70)

if result.documents:
    doc = result.documents[0]
    print(f"\n📄 Document: {doc.filename} | Pages: {doc.total_pages}")
    
    # Build a flat field map from all pages
    extracted = {}
    for page in doc.pages:
        print(f"\n  [Page {page.page_number}] {len(page.extracted_fields)} fields extracted")
        for f in page.extracted_fields:
            extracted[f.key] = f.value
    
    print("\n" + "-"*70)
    print(f"{'FIELD':<40} {'EXPECTED':<20} {'OCR GOT':<20} {'MATCH'}")
    print("-"*70)
    
    all_match = True
    for field, expected_val in EXPECTED.items():
        # Try exact key match, then normalized
        got = extracted.get(field, "")
        if not got:
            # try case-insensitive search
            for k, v in extracted.items():
                if k.lower().strip() == field.lower().strip():
                    got = v
                    break
        
        match = "✅" if got.strip().lower() == expected_val.strip().lower() else "❌"
        if match == "❌":
            all_match = False
        print(f"  {field:<38} {expected_val:<20} {got:<20} {match}")
    
    print("-"*70)
    print(f"\n{'✅ ALL FIELDS MATCH!' if all_match else '❌ SOME FIELDS DO NOT MATCH — see above'}")
    
    # Show fields extracted but NOT in expected (extra fields)
    print(f"\n📊 All fields extracted by OCR:")
    for k, v in extracted.items():
        in_expected = k in EXPECTED
        print(f"  {'✅' if in_expected else '  '} '{k}': '{v}'")
else:
    print("❌ No documents returned from OCR!")
