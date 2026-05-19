import re

with open('/home/redspark/.gemini/antigravity/brain/950277a7-bd7f-421d-b9b6-7987587f6e04/.system_generated/logs/overview.txt', 'r') as f:
    lines = f.readlines()

for line in lines[-500:]:
    if 'Extracted' in line or 'Metering R' in line or 'Ratio' in line:
        print(line.strip()[:200])
