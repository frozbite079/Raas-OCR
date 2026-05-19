import asyncio
import sys
from services.ocr_service import OCRService

async def run():
    try:
        ocr = OCRService()
        doc_data, _ = await ocr.process_document(
            file_path="2.pdf",
            doc_type=None,
            include_images=False,
            include_html=True
        )
        print(f"Detected Doc Type: {doc_data.category}")
        print(f"Total extracted fields: {sum(len(p.extracted_fields) for p in doc_data.pages)}")
        print(f"HTML output length: {len(doc_data.filled_html) if doc_data.filled_html else 0}")
        if doc_data.filled_html:
            print("Preview of HTML start:")
            print(doc_data.filled_html[:200])
    except Exception as e:
        print(f"Error processing 2.pdf: {e}")

if __name__ == "__main__":
    asyncio.run(run())
