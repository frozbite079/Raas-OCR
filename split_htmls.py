import os

base_dir = '/home/redspark/Pictures/Raas-OCR/html_pages'
src1 = os.path.join(base_dir, 'double page', 'current_transformer_test_report.html')
src2 = os.path.join(base_dir, 'double page', 'rmu_test_report_page_2.html')
dest1 = os.path.join(base_dir, 'rmu_test_report_page_1.html')
dest2 = os.path.join(base_dir, 'rmu_test_report_page_2.html')

with open(src1, 'r') as f:
    ct_lines = f.readlines()

with open(src2, 'r') as f:
    rmu2_lines = f.readlines()

# Page 1:
# CT report from line 1 to 408 (index 0 to 407)
# then </div></body></html>
page1_content = ct_lines[:408] + ['    </div>\n', '</body>\n', '</html>\n']
with open(dest1, 'w') as f:
    f.writelines(page1_content)

# Page 2:
# CT report from line 1 to 167 (index 0 to 166) - head and <body> <div class="report-page">
page2_head = ct_lines[:167]
# Change title
for i, line in enumerate(page2_head):
    if '<title>' in line:
        page2_head[i] = line.replace('</title>', ' - Page 2</title>')

# CT report lines 410-438 (index 409 to 437) - RMU specifications
page2_spec = ct_lines[409:438]

# RMU2 report from line 211 to 483 (index 210 to 482) - Rest of page 2
# Look at rmu_test_report_page_2.html lines 210 to 483
# Actually, the file has 483 lines, so index 210 to 483
page2_rest = rmu2_lines[210:]

page2_content = page2_head + page2_spec + page2_rest
with open(dest2, 'w') as f:
    f.writelines(page2_content)

print("Split completed.")
