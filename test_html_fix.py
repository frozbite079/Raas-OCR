#!/usr/bin/env python3
"""
Test script to demonstrate the fix for empty HTML files issue.
This simulates what happens when processing 2.pdf with OCR.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.html_template_service import html_template_service
from models.schemas import PageData, ExtractedField


async def test_pt_report_fix():
    """
    Simulate processing 2.pdf (PT TEST REPORT) and verify HTML filling works.
    """
    print("=" * 70)
    print("TESTING PT TEST REPORT HTML FILLING FIX")
    print("=" * 70)
    print()

    # Simulate OCR extracted data from 2.pdf
    # These are typical fields that would be extracted from a PT Test Report
    simulated_ocr_data = PageData(
        page_number=1,
        title="PT TEST REPORT",
        category="PT TEST REPORT",
        extracted_fields=[
            ExtractedField(key="Client", value="Kashish Industries Ltd."),
            ExtractedField(key="Plant", value="Kashish Power Plant"),
            ExtractedField(key="Date", value="14-04-2024"),
            ExtractedField(key="Feeder Name", value="Feeder K-11"),
            ExtractedField(key="Make", value="Kashish Electrical"),
            ExtractedField(key="Phase", value="R"),
            ExtractedField(key="PT Ratio", value="11kV/110V"),
            ExtractedField(key="Sr. No", value="KPT-2024-001"),
            ExtractedField(key="VA Core 1", value="15 VA"),
            ExtractedField(key="VA Core 2", value="10 VA"),
            ExtractedField(key="VA Core 3", value="5 VA"),
            ExtractedField(key="Accuracy Class Core 1", value="0.2"),
            ExtractedField(key="Accuracy Class Core 2", value="0.5"),
            ExtractedField(key="Accuracy Class Core 3", value="1.0"),
            ExtractedField(key="Primary Voltage R", value="11000 V"),
            ExtractedField(key="Secondary Voltage R", value="63.5 V"),
            ExtractedField(key="Secondary Winding Resistance R", value="0.25 Ω"),
            ExtractedField(key="Ratio R", value="173.28"),
            ExtractedField(key="Primary Voltage Y", value="11000 V"),
            ExtractedField(key="Secondary Voltage Y", value="63.5 V"),
            ExtractedField(key="Secondary Winding Resistance Y", value="0.24 Ω"),
            ExtractedField(key="Ratio Y", value="173.28"),
            ExtractedField(key="Primary Voltage B", value="11000 V"),
            ExtractedField(key="Secondary Voltage B", value="63.5 V"),
            ExtractedField(key="Secondary Winding Resistance B", value="0.25 Ω"),
            ExtractedField(key="Ratio B", value="173.28"),
            ExtractedField(
                key="Remarks", value="All tests passed. PT is in good condition."
            ),
        ],
    )

    print(
        f"Simulated OCR extraction: {len(simulated_ocr_data.extracted_fields)} fields"
    )
    print()

    # Load original template
    original_html = html_template_service.load_template("pt_test_report.html")

    # Fill template with OCR data
    filled_html = html_template_service.process_document_html(
        "PT TEST REPORT", [simulated_ocr_data]
    )

    # Verify the filling worked
    print("Verification Results:")
    print("-" * 70)

    # Check specific key fields
    key_fields = {
        "Client": "Kashish Industries Ltd.",
        "Plant": "Kashish Power Plant",
        "Date": "14-04-2024",
        "Feeder Name": "Feeder K-11",
        "Make": "Kashish Electrical",
    }

    all_fields_found = True
    for field_name, expected_value in key_fields.items():
        if expected_value in filled_html:
            print(f"✓ {field_name:20} : {expected_value}")
        else:
            print(f"❌ {field_name:20} : {expected_value} (NOT FOUND)")
            all_fields_found = False

    print()
    print("File Size Comparison:")
    print(f"  Original template: {len(original_html)} bytes")
    print(f"  Filled template:    {len(filled_html)} bytes")
    print(f"  Difference:         {len(filled_html) - len(original_html)} bytes")
    print()

    if all_fields_found and filled_html:
        print("✅ SUCCESS: HTML template is now being filled correctly!")
        print("   The HTML template is being filled correctly.")
        print()
        return True
    else:
        print("❌ FAILED: Template filling still has issues")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_pt_report_fix())
    print()
    print("=" * 70)
    sys.exit(0 if success else 1)
