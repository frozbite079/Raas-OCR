import asyncio
from services.ocr_service import OCRService

async def run():
    ocr = OCRService()
    doc_data, _ = await ocr.process_document(
        file_path="1.pdf",
        doc_type="TEST CERTIFICATE OF POWER TRANSFORMER",
        include_images=False,
        include_html=True
    )
    for page in doc_data.pages:
        for field in page.extracted_fields:
            if "Tap" in field.key or "Vector Group" in field.key or "Magnetic Balance" in field.key or "Cooling" in field.key:
                print(f"{field.key}: '{field.value}'")
                
if __name__ == "__main__":
    asyncio.run(run())
