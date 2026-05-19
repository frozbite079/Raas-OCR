from services.html_template_service import html_template_service
from models.schemas import PageData, ExtractedField
html2 = html_template_service.load_template("rmu_test_report_page_2.html")
p2 = PageData(page_number=2, extracted_fields=[
    ExtractedField(key="Breaking Capacity", value="1"),
    ExtractedField(key="CT R Ratio", value="4545")
])
filled = html_template_service.fill_template_with_data(html2, [p2], "TEST CERTIFICATE OF NUMERICAL RELAY RMU")
from bs4 import BeautifulSoup
soup = BeautifulSoup(filled, "html.parser")
inputs = soup.find_all("input")
print(f"Input 0: {inputs[0].get('value')}")
print(f"Input 1: {inputs[1].get('value')}")
for i, inp in enumerate(inputs):
    if inp.get('value') and inp.get('value') != "":
        print(f"Input {i}: {inp.get('value')}")
