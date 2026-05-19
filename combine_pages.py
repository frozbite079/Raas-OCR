import os
import sys

def combine_files():
    with open("/home/redspark/Pictures/Raas-OCR/html_pages/rmu_test_report_page_1.html", "r") as f:
        page1 = f.read()

    with open("/home/redspark/Pictures/Raas-OCR/html_pages/rmu_test_report_page_2.html", "r") as f:
        page2 = f.read()

    start_idx = page1.find("<!-- Page 2 Content properly integrated -->")
    end_idx = page1.rfind("</body>")

    start2_idx = page2.find("<div class=\"check-list-container\" style=\"margin-top: 30px;\">")
    end2_idx = page2.rfind("</div>\n\n</body>")

    if start_idx != -1 and start2_idx != -1:
        combined_body = page1[:start_idx] + \
                        "        <div class=\"page-break\"></div> <!-- FORCE PRINT PAGE BREAK HERE -->\n\n" + \
                        page2[start2_idx:end2_idx] + \
                        "\n    </div>\n</body>\n</html>"
        
        with open("/home/redspark/Pictures/Raas-OCR/html_pages/test_certificate_of_numerical_relay_rmu.html", "w") as f:
            f.write(combined_body)
        print("Combined successfully.")
    else:
        print("Could not find markers.")

if __name__ == "__main__":
    combine_files()
