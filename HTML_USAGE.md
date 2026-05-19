# How to Get HTML Output

## Problem Solved ✅

**Why you weren't seeing HTML before:**
- The system only had HTML template for "TEST CERTIFICATE OF POWER TRANSFORMER"
- If your PDF was a different document type, no HTML was generated
- Now we have a **Generic HTML Generator** that works for ANY document type!

---

## How to Use Now

### Option 1: Postman (Easiest)

**Step 1: Start Server**
```bash
python main.py
```

**Step 2: Test in Postman**
```
POST http://localhost:8000/api/ocr/extract?include_html=true

Body: form-data
  - files: [upload your PDF or image]
  - include_html: true
```

**Step 3: Check Response**
```json
{
  "success": true,
  "documents": [
    {
      "filled_html": "<!DOCTYPE html>...",  ← This is the HTML!
      "pages": [...]
    }
  ]
}
```

**Step 4: Save and View HTML**
1. Copy the `filled_html` value
2. Paste into a new file: `output.html`
3. Open in browser

---

### Option 2: Command Line (Quick Test)

```bash
# Upload and get HTML
curl -X POST "http://localhost:8000/api/ocr/extract?include_html=true" \
  -F "files=@your_document.pdf" \
  -o response.json

# Extract HTML from response
python3 -c "
import json
with open('response.json') as f:
    data = json.load(f)
    html = data['documents'][0]['filled_html']
    with open('result.html', 'w') as o:
        o.write(html)
print('Saved to result.html')
"

# Open in browser
xdg-open result.html  # Linux
# or start result.html  # Windows
```

---

### Option 3: Python Script

```python
import requests

url = "http://localhost:8000/api/ocr/extract?include_html=true"
files = {'files': open('your_document.pdf', 'rb')}

response = requests.post(url, files=files)
data = response.json()

# Save HTML
html = data['documents'][0]['filled_html']
with open('filled_output.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved to filled_output.html - open in browser!")
```

---

## What You'll See

### If Document Type Has Specific Template:
- **Example:** "TEST CERTIFICATE OF POWER TRANSFORMER"
- **Result:** Filled professional form matching the original document layout

### If Document Type Has No Template:
- **Example:** Any other document type (PT, CT, VCB, etc.)
- **Result:** Generic HTML form showing all extracted fields in a clean table

Both look great and are ready to print or save!

---

## Debugging

If you still don't see HTML, check the console output:

```bash
# Start server with verbose output
python main.py

# Upload your file and watch for debug messages:
# [DEBUG] Attempting to fill HTML for document type: ...
# [DEBUG] HTML template not found for type: ..., using generic HTML
# [DEBUG] Generic HTML generated, length: ...
```

The debug messages will show:
- What document type was detected
- Whether a template was found
- If generic HTML was used as fallback
- The length of generated HTML

---

## Check Your Document Type

Want to know what type your PDF will be detected as?

```bash
python check_pdf_type.py your_document.pdf
```

This will show you the detected type and whether an HTML template exists for it.

---

## Summary

✅ **include_html=true** now works for **ANY** document type
✅ **Specific templates** available for Power Transformer
✅ **Generic HTML** auto-generated for all other types
✅ **Debug output** shows what's happening

Try it now! Upload any PDF with `include_html=true` and you'll get HTML.
