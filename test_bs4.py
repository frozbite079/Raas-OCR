from bs4 import BeautifulSoup
import sys

with open("html_pages/test_certificate_power_transformer.html", "r", encoding="utf-8") as f:
    orig = f.read()

soup = BeautifulSoup(orig, "html.parser")
out = str(soup)

print("Original length:", len(orig))
print("BS4 length:", len(out))

with open("orig.html", "w", encoding="utf-8") as f: f.write(orig)
with open("out.html", "w", encoding="utf-8") as f: f.write(out)
