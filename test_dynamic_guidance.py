"""
Test: Verify that extract_template_guidance() dynamically generates
correct table extraction rules from the HTML template's data-field attributes.
"""
from services.html_template_service import html_template_service

doc_types = [
    "TEST CERTIFICATE OF HT SWITCHGEAR PANEL",
    "TEST CERTIFICATE OF TRANSFORMER",
    "VCB MAINTENANCE CHECK LIST",
    "SIEMENS RMU",
]

for dt in doc_types:
    print(f"\n{'='*80}")
    print(f"DOCUMENT TYPE: {dt}")
    print(f"{'='*80}")
    
    guidance = html_template_service.extract_template_guidance(dt)
    if guidance:
        print(guidance)
    else:
        print("  (no template guidance generated)")
    
    fields = html_template_service.get_all_template_data_fields(dt)
    print(f"\n  Total data-field attributes found: {len(fields)}")
    for f in fields[:10]:
        print(f"    - {f}")
    if len(fields) > 10:
        print(f"    ... and {len(fields) - 10} more")
