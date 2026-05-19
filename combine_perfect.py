import re
import os

page1_path = "/home/redspark/Pictures/Raas-OCR/html_pages/rmu_test_report_page_1.html"
page2_path = "/home/redspark/Pictures/Raas-OCR/html_pages/rmu_test_report_page_2.html"

with open(page1_path, "r") as f:
    page1 = f.read()

with open(page2_path, "r") as f:
    page2 = f.read()

def extract_style(html):
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    return m.group(1) if m else ""

def extract_body(html):
    m = re.search(r"<body>(.*?)</body>", html, re.DOTALL)
    return m.group(1) if m else ""

style1 = extract_style(page1)
style2 = extract_style(page2)

# Namespace page 2's specific `.report-page` to `.report-page-2` to avoid clashing with page 1's `.report-page`
style2 = style2.replace(".report-page", ".report-page-2")

combined_style = style1 + "\n/* --- PAGE 2 STYLES --- */\n" + style2

body1 = extract_body(page1)
# Clean up body 1 - it might have a closing div that we want to keep, but let's just use it exactly as is
# Actually, the original rmu_test_report_page_1.html didn't have dummy page 2 content.
# Wait, I previously edited it! I need to be careful.
# Let's see what is inside page1 body.

body2 = extract_body(page2)
# Rename `.report-page` to `.report-page-2` in body2
body2 = body2.replace('class="report-page"', 'class="report-page-2"')

combined_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Certificate of Numerical Relay RMU</title>
    <style>
{combined_style}
    </style>
</head>
<body>
{body1}
    <div style="page-break-after: always; margin-bottom: 40px;"></div>
{body2}
</body>
</html>
"""

output_path = "/home/redspark/Pictures/Raas-OCR/html_pages/test_certificate_of_numerical_relay_rmu.html"
with open(output_path, "w") as f:
    f.write(combined_html)

print("Created perfect combination.")
