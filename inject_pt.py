import re
from models.schemas import PT_TEST_REPORT_KEYS

with open("html_pages/pt_test_report.html", "r", encoding="utf-8") as f:
    content = f.read()

# We need to find all <input> and <input ...> tags and sequential insert `data-field="..."`.
# We can use a replacer function for re.sub to consume from PT_TEST_REPORT_KEYS
keys_iter = iter(PT_TEST_REPORT_KEYS + ["Remarks"])

def replace_input(match):
    full_tag = match.group(0)
    
    # Try getting the next key
    try:
        key = next(keys_iter)
    except StopIteration:
        return full_tag  # No more keys
        
    return full_tag.replace('<input ', f'<input data-field="{key}" ')

# Match <input...> specifically taking care of case
new_content = re.sub(r'(?i)<input\b', replace_input, content)

with open("html_pages/pt_test_report.html", "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Injected {len(PT_TEST_REPORT_KEYS) + 1} fields into pt_test_report.html")
