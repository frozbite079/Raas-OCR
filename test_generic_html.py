#!/usr/bin/env python3
"""Test generic HTML generator"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.schemas import PageData, ExtractedField
from services.generic_html_generator import generate_generic_html

# Create test data
test_data = PageData(
    page_number=1,
    title="Sample Document",
    category="TEST DOCUMENT",
    extracted_fields=[
        ExtractedField(key="Field 1", value="Value 1"),
        ExtractedField(key="Field 2", value="Value 2"),
        ExtractedField(key="Field 3", value="Value 3"),
        ExtractedField(key="Client", value="ABC Corp"),
        ExtractedField(key="Date", value="2024-01-15"),
    ],
)

# Generate HTML
html = generate_generic_html(test_data)

# Save to file
output_file = "test_generic_html.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Generic HTML generated successfully!")
print(f"✅ Output saved to: {output_file}")
print(f"✅ HTML length: {len(html)} characters")
print(f"\nOpen {output_file} in your browser to see the result")
