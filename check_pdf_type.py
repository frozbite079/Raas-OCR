#!/usr/bin/env python3
"""
Quick test to see what document type is detected from your PDF.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ocr_service import OCRService
from PIL import Image
from pdf2image import convert_from_path
import asyncio


async def check_document_type(pdf_path: str):
    """Check what document type is detected"""

    print(f"Analyzing: {pdf_path}")
    print("=" * 60)

    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=200)

    if not images:
        print("❌ No images found in PDF")
        return

    print(f"✓ PDF has {len(images)} page(s)")

    # Initialize OCR service
    ocr_service = OCRService()

    # Detect document type from first page
    doc_type = await ocr_service._detect_document_type(images[0])

    print(f"✓ Detected document type: {doc_type}")
    print()

    # Check if HTML template exists
    from services.html_template_service import DOCUMENT_HTML_MAPPING

    html_file = DOCUMENT_HTML_MAPPING.get(doc_type)
    if html_file:
        print(f"✓ HTML template found: {html_file}")
        print("✓ include_html=true should work!")
    else:
        print(f"❌ No HTML template for: {doc_type}")
        print()
        print("Available templates:")
        for dt, hf in DOCUMENT_HTML_MAPPING.items():
            print(f"  - {dt}: {hf}")

    print()
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_pdf_type.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    asyncio.run(check_document_type(pdf_path))
