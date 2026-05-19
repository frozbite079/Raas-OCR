import re
from bs4 import BeautifulSoup
from models.schemas import PT_TEST_REPORT_KEYS

print("Injecting data-field attributes into pt_test_report.html...")

with open("html_pages/pt_test_report.html", "r", encoding="utf-8") as f:
    content = f.read()

keys_iter = iter(PT_TEST_REPORT_KEYS + ["Remarks"])

def replace_input(match):
    full_tag = match.group(0)
    if 'data-field' in full_tag:
        return full_tag  # Already has it
    try:
        key = next(keys_iter)
    except StopIteration:
        return full_tag
    
    # insert data-field right after <input
    return full_tag.replace('<input ', f'<input data-field="{key}" ')

# There are exactly 71 inputs in pt_test_report.html and exactly 71 keys in our iterator.
content = re.sub(r'(?i)<input\b', replace_input, content)

with open("html_pages/pt_test_report.html", "w", encoding="utf-8") as f:
    f.write(content)

print("pt_test_report.html updated successfully!")
