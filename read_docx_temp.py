import zipfile
import xml.etree.ElementTree as ET

def read_docx(path):
    z = zipfile.ZipFile(path)
    xml_content = z.read('word/document.xml')
    tree = ET.XML(xml_content)
    namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    text = '\n'.join([node.text for node in tree.findall('.//w:t', namespace) if node.text])
    print(text)

read_docx('/home/redspark/Pictures/Raas-OCR/New.Project_Scope(Quality&Compliance.Platform).docx')
