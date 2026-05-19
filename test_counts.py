import re
html1 = open('html_pages/rmu_test_report_page_1.html').read()
html2 = open('html_pages/rmu_test_report_page_2.html').read()
p1 = len(re.findall(r'<input\b(?![^>]*?data-field)[^>]*>', html1, re.IGNORECASE))
p2 = len(re.findall(r'<input\b(?![^>]*?data-field)[^>]*>', html2, re.IGNORECASE))

with open("counts.txt", "w") as f:
    f.write(f"Page 1 inputs: {p1}\nPage 2 inputs: {p2}\n")
