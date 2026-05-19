import sys
import os
import base64
import io
from pdf2image import convert_from_path
from PIL import Image

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

def convert_pdf_to_html(pdf_path: str):
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found.")
        return

    print(f"Processing PDF: {pdf_path}")
    
    # Using gpt-4o-mini as specified by you. 
    # (Note: gpt-4o might yield even better HTML alignment, but mini is faster/cheaper)
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=16000)

    print("Converting PDF to images...")
    try:
        images = convert_from_path(pdf_path, dpi=200)
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return

    system_prompt = SystemMessage(
        content="You are an expert HTML developer specialized in document recreation. Your task is to output an EXACT HTML/CSS recreation of the provided document images.\n\n"
                "CRITICAL STYLING AND DATA REQUIREMENTS:\n"
                "1. EMPTY TEMPLATE / FORM ONLY: DO NOT extract any filled-in data, handwritten values, or specific test results. You must recreate the EMPTY FORM/TEMPLATE with all all its headers, labels, and table structures perfectly laid out. Leave the input areas/cells completely blank.\n"
                "2. VISUAL FIDELITY & TABLES: The HTML must look identical to the PDF structure. Use explicit table borders (`border: 1px solid black;`) for all tables and data grids. Ensure columns and rows match the original document exactly.\n"
                "3. A4 LAYOUT: Wrap everything in a `<div class=\"a4-page\">`. Use the following CSS:\n"
                "   body { background-color: #f0f2f5; margin: 0; padding: 40px; display: flex; justify-content: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }\n"
                "   .a4-page { width: 210mm; min-height: 297mm; padding: 20mm; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); box-sizing: border-box; }\n"
                "   table { width: 100%; border-collapse: collapse; margin-bottom: 20px; table-layout: fixed; }\n"
                "   th, td { border: 1px solid #000; padding: 8px; text-align: left; vertical-align: top; font-size: 12px; height: 25px; }\n"
                "   .no-border td, .no-border th { border: none !important; }\n"
                "   h1, h2 { text-align: center; margin-top: 0; text-transform: uppercase; }\n"
                "4. GRID STRUCTURES: If a section looks like a table but has no borders, use the `.no-border` class, but ensure the structural alignment is perfectly preserved.\n\n"
                "Output ONLY the complete HTML code starting with `<!DOCTYPE html>`. Ensure no markdown wrappers."
    )

    content_parts = []
    
    for i, img in enumerate(images):
        print(f"Encoding page {i + 1}/{len(images)}...")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        content_parts.append({"type": "text", "text": f"--- Page {i + 1} ---"})
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_base64}"}
        })

    content_parts.append({
        "type": "text", 
        "text": "Convert these pages into a single cohesive HTML file that perfectly replicates the original document."
    })

    human_message = HumanMessage(content=content_parts)

    print("Sending to the model to generate HTML (this may take a minute depending on page count)...")
    chain = model | StrOutputParser()
    html_output = chain.invoke([system_prompt, human_message]).strip()
    
    # Strip markdown if the model hallucinates it despite instructions
    if html_output.startswith("```html"):
        html_output = html_output.split("```html", 1)[1]
        html_output = html_output.rsplit("```", 1)[0].strip()
    elif html_output.startswith("```"):
        html_output = html_output.split("```", 1)[1]
        html_output = html_output.rsplit("```", 1)[0].strip()

    output_filename = os.path.splitext(os.path.basename(pdf_path))[0] + "_output.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_output)
    
    print(f"\nDone! HTML output saved to {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python teting.py <path_to_pdf>")
    else:
        convert_pdf_to_html(sys.argv[1])