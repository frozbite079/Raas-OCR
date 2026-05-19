from services.html_template_service import html_template_service
from models.schemas import PageData, ExtractedField

# Simulate OCR extraction for Page 1
p1 = PageData(page_number=1, extracted_fields=[
    ExtractedField(key="Client", value="Ramu Jain"),
    ExtractedField(key="RMU Make", value="Schneider"),
    ExtractedField(key="Def. Time Earth Fault Protection", value="4")
])

# Simulate OCR extraction for Page 2
p2 = PageData(page_number=2, extracted_fields=[
    ExtractedField(key="Breaking Capacity", value="10kA"),
    ExtractedField(key="2.0 General Check-up", value="OK"),
    ExtractedField(key="3.0 Control Circuit and Operational Tests", value="Checked"),
    ExtractedField(key="CT R Ratio", value="4545"),
    ExtractedField(key="Remarks Footer", value="All tests passed")
])

filled = html_template_service.process_document_html("TEST CERTIFICATE OF NUMERICAL RELAY RMU", [p1, p2])

from bs4 import BeautifulSoup
soup = BeautifulSoup(filled, "html.parser")
inputs = soup.find_all("input")

# Print some key inputs to verify correct injection
print("--- Page 1 Inputs ---")
print(f"Client (index 0): {inputs[0].get('value')}")
print(f"Earth Fault (index ~38): {inputs[38].get('value')}")
print(f"RMU Make (index 53): {inputs[53].get('value')}")

print("\n--- Page 2 Inputs ---")
print(f"Breaking Capacity (index 57): {inputs[57].get('value')}")
print(f"2.0 General Check-up (index 59): {inputs[59].get('value')}")
print(f"3.0 Control Circuit (index 65): {inputs[65].get('value')}")
print(f"CT R Ratio (index 75): {inputs[75].get('value')}")
print(f"Remarks Footer (index 110): {inputs[110].get('value')}")
