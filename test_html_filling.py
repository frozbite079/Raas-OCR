#!/usr/bin/env python3
"""
Test script for HTML template filling functionality.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.schemas import PageData, ExtractedField
from services.html_template_service import html_template_service

# Create test page data with extracted fields
test_page_data = PageData(
    page_number=1,
    title="TEST CERTIFICATE OF POWER TRANSFORMER",
    category="TEST CERTIFICATE OF POWER TRANSFORMER",
    extracted_fields=[
        ExtractedField(key="Client", value="ABC Corporation"),
        ExtractedField(key="Plant", value="Power Station A"),
        ExtractedField(key="Location", value="Mumbai"),
        ExtractedField(key="Tested On", value="2024-01-15"),
        ExtractedField(key="Tested By", value="John Doe"),
        ExtractedField(key="Comp. Code", value="PC-1234"),
        ExtractedField(key="Make", value="ABB"),
        ExtractedField(key="Serial No.", value="SN-2024-001"),
        ExtractedField(key="Rating in MVA", value="25"),
        ExtractedField(key="Voltage Ratio", value="220/33 kV"),
        ExtractedField(key="Type of Cooling", value="ONAF"),
        ExtractedField(key="Vector Group", value="Dyn11"),
        ExtractedField(key="% Impedance", value="10.5"),
        ExtractedField(key="Tap Changer", value="OLTC"),
        ExtractedField(key="No. Of Taps", value="17"),
    ],
)

# Test HTML filling
print("Testing HTML Template Filling...")
print("=" * 60)

filled_html = html_template_service.process_document_html(
    "TEST CERTIFICATE OF POWER TRANSFORMER", [test_page_data]
)

if filled_html:
    print("✓ HTML filling successful!")
    print(f"✓ Generated HTML length: {len(filled_html)} characters")

    # Check if the template was filled with values
    test_values = ["ABC Corporation", "Power Station A", "ABB", "25"]
    found_count = sum(1 for val in test_values if val in filled_html)

    print(f"✓ Test values found: {found_count}/{len(test_values)}")

    if found_count == len(test_values):
        print("\n✓ All test values successfully filled into HTML!")
    else:
        print(
            f"\n⚠ Only {found_count} out of {len(test_values)} test values found in HTML"
        )

    # Save sample output
    output_file = "test_filled_output.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(filled_html)
    print(f"\n✓ Saved filled HTML to: {output_file}")

else:
    print("✗ HTML filling failed - template not found")
    sys.exit(1)

print("=" * 60)
print("Test complete!")
