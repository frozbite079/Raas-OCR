"""
Generic HTML Generator
Creates a simple HTML form for any document type with OCR data.
"""

from models.schemas import PageData


def generate_generic_html(page_data: PageData) -> str:
    """
    Generate a simple HTML form to display OCR data for any document type.

    Args:
        page_data: Extracted OCR data

    Returns:
        HTML string
    """

    fields_html = ""
    for field in page_data.extracted_fields:
        fields_html += f"""
        <div class="field-row">
            <label class="field-label">{field.key}:</label>
            <input type="text" class="field-input" value="{field.value}" readonly>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_data.title or "OCR Extracted Data"}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .document-type {{
            background: #007bff;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            display: inline-block;
            margin-bottom: 20px;
            font-weight: bold;
        }}
        .field-row {{
            display: flex;
            margin-bottom: 15px;
            align-items: center;
        }}
        .field-label {{
            flex: 0 0 300px;
            font-weight: bold;
            color: #555;
            padding-right: 15px;
        }}
        .field-input {{
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            background-color: #f9f9f9;
        }}
        .field-input:focus {{
            outline: none;
            border-color: #007bff;
            background-color: white;
        }}
        .info {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .total-fields {{
            background: #e7f3ff;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
            color: #007bff;
        }}
        @media print {{
            body {{ background: white; margin: 0; }}
            .container {{ box-shadow: none; padding: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{page_data.title or "OCR Extracted Data"}</h1>

        <div class="document-type">
            {page_data.category or "Unknown Document Type"}
        </div>

        <div class="info">
            Page: {page_data.page_number} | Fields extracted: {len(page_data.extracted_fields)}
        </div>

        <div class="total-fields">
            {len(page_data.extracted_fields)} Fields Extracted
        </div>

        {fields_html}
    </div>
</body>
</html>"""

    return html
