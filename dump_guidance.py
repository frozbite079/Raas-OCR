#!/usr/bin/env python3
"""Dump the dynamic guidance text that gets sent to the LLM for this document type."""
import os, sys
os.chdir("/home/redspark/Pictures/Raas-OCR")
sys.path.insert(0, ".")
from services.html_template_service import html_template_service
g = html_template_service.extract_template_guidance("SERVICE REPORT FOR LV CIRCUIT BREAKER")
print("=" * 80)
print("GUIDANCE SENT TO LLM:")
print("=" * 80)
print(g)
print("=" * 80)
print(f"Total length: {len(g)} chars")
