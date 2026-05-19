#!/usr/bin/env python3
"""
Quick test to diagnose why HTML templates are empty.
"""

import sys
import os
import re
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.html_template_service import html_template_service
from services.ocr_service import OCRService


def check_template_data_fields():
    """Check which templates have data-field attributes"""
    print("=" * 70)
    print("HTML TEMPLATE DIAGNOSTIC REPORT")
    print("=" * 70)
    print()

    html_dir = "html_pages"
    html_files = os.listdir(html_dir)

    issues_found = 0

    for html_file in html_files:
        if html_file.endswith(".html"):
            with open(os.path.join(html_dir, html_file), "r", encoding="utf-8") as f:
                content = f.read()

            # Count total inputs
            input_pattern = re.compile(r"<input[^>]*>", re.IGNORECASE)
            total_inputs = len(input_pattern.findall(content))

            # Count inputs with data-field
            data_field_pattern = re.compile(
                r'<input[^>]*?data-field\s*=\s*["\']([^"\']+)["\'][^>]*>', re.IGNORECASE
            )
            data_field_matches = data_field_pattern.findall(content)
            data_field_inputs = len(data_field_matches)

            if total_inputs > 0:
                if data_field_inputs == total_inputs:
                    status = "✓ PASS"
                    msg = "All inputs have data-field"
                elif data_field_inputs > 0:
                    status = "⚠️  PARTIAL"
                    msg = f"Only {data_field_inputs}/{total_inputs} have data-field"
                    issues_found += 1
                else:
                    status = "❌ FAIL"
                    msg = f"No data-field attributes (0/{total_inputs})"
                    issues_found += 1

                print(f"{status} {html_file:50}")
                print(f"       {msg}")
                print()

    print("=" * 70)
    if issues_found > 0:
        print(f"❌ {issues_found} template(s) will produce empty HTML files")
        print()
        print("REASON: The fill_template_with_data() method uses this regex:")
        print("  <input[^>]*?data-field\\s*=\\s*[\"\\']([^\"\\']+)[\"\\'][^>]*>")
        print()
        print("It ONLY fills input fields that have data-field attributes.")
        print("Without these attributes, fields remain empty!")
        print()
        print("SOLUTION: Add data-field attributes to all input fields, OR")
        print(
            "         modify fill_template_with_data() to handle fields without them."
        )
    else:
        print("✓ All templates have data-field attributes configured correctly!")
    print("=" * 70)


async def test_pt_report_html():
    """Test actual PT Report HTML filling"""
    print("\n" + "=" * 70)
    print("TESTING PT REPORT HTML FILLING")
    print("=" * 70)
    print()

    # Create sample data that would be extracted from OCR
    from models.schemas import PageData, ExtractedField

    sample_page = PageData(
        page_number=1,
        title="PT TEST REPORT",
        category="PT TEST REPORT",
        extracted_fields=[
            ExtractedField(key="Client", value="ABC Industries"),
            ExtractedField(key="Plant", value="Main Plant"),
            ExtractedField(key="Date", value="15-04-2024"),
            ExtractedField(key="Feeder Name", value="Feeder-123"),
            ExtractedField(key="Make", value="ECS"),
            ExtractedField(key="Phase", value="R"),
        ],
    )

    # Try to fill the template
    filled_html = html_template_service.process_document_html(
        "PT TEST REPORT", [sample_page]
    )

    if filled_html:
        print(f"✓ HTML generated successfully ({len(filled_html)} chars)")

        # Check if fields were actually filled
        sample_values = [
            "ABC Industries",
            "Main Plant",
            "15-04-2024",
            "Feeder-123",
            "ECS",
        ]
        filled_count = sum(1 for val in sample_values if val in filled_html)

        print(f"  Sample values found in HTML: {filled_count}/{len(sample_values)}")

        if filled_count == 0:
            print("  ❌ NO fields were filled! The template is empty.")
            print()
            print("This confirms the issue: Input fields lack data-field attributes.")
        else:
            print("  ✓ Fields were filled successfully!")
    else:
        print("❌ Failed to generate HTML")

    print("=" * 70)


if __name__ == "__main__":
    check_template_data_fields()
    asyncio.run(test_pt_report_html())
