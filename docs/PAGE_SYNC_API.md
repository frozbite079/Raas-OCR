# Raas-OCR API - Page Synchronization Guide

## Overview

This document explains how to implement **synchronized page navigation** in the split-screen OCR editor UI, where:
- **Left panel**: Shows the original PDF/image page
- **Right panel**: Shows the extracted OCR data for that page

When the user navigates to a different page in the PDF viewer (left), the extracted data (right) must update to show the corresponding page's data.

---

## API Workflow

### Step 1: Upload Document

```http
POST /api/ocr/extract
Content-Type: multipart/form-data

files: [your_document.pdf]
include_images: false  # Optional: set true to get base64 images inline
```

**Response:**
```json
{
  "success": true,
  "message": "Processed 1 document(s)",
  "documents": [{
    "document_id": "abc-123-def-456",  // ← Use this for page requests
    "filename": "test.pdf",
    "total_pages": 5,
    "pages": [
      { "page_number": 1, "title": "...", "extracted_fields": [...] },
      { "page_number": 2, "title": "...", "extracted_fields": [...] },
      ...
    ]
  }]
}
```

**Save the `document_id`** - you'll need it for all subsequent page requests.

---

### Step 2: Display Page with Synchronized Data

When user navigates to page N:

#### Get Page Image (for left panel)
```http
GET /api/documents/{document_id}/pages/{page_num}/image?format=base64
```

**Response:**
```json
{
  "document_id": "abc-123-def-456",
  "page_number": 3,
  "total_pages": 5,
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

To display as raw PNG:
```http
GET /api/documents/{document_id}/pages/{page_num}/image?format=raw
```
Returns: `Content-Type: image/png` binary data

#### Get Extracted Data (for right panel)
```http
GET /api/documents/{document_id}/pages/{page_num}
```

**Response:**
```json
{
  "document_id": "abc-123-def-456",
  "page_number": 3,
  "total_pages": 5,
  "page_data": {
    "page_number": 3,
    "title": "ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER)",
    "category": "VCB",
    "extracted_fields": [
      { "key": "Certificate No", "value": "67-VCB-2024" },
      { "key": "Customer", "value": "ABC Industries" },
      { "key": "WO No", "value": "WO-1123" },
      ...
    ]
  }
}
```

---

## Frontend Implementation

### Synchronization Logic (Pseudocode)

```javascript
// On document upload
const response = await uploadDocument(pdfFile);
const documentId = response.documents[0].document_id;
const totalPages = response.documents[0].total_pages;

// Initialize with page 1
let currentPage = 1;
await loadPage(currentPage);

// Page navigation handler
async function loadPage(pageNumber) {
  // Fetch both in parallel for performance
  const [imageResponse, dataResponse] = await Promise.all([
    fetch(`/api/documents/${documentId}/pages/${pageNumber}/image?format=base64`),
    fetch(`/api/documents/${documentId}/pages/${pageNumber}`)
  ]);
  
  // Update left panel (original image)
  const imageData = await imageResponse.json();
  leftPanel.src = `data:image/png;base64,${imageData.image_base64}`;
  
  // Update right panel (extracted data)
  const extractedData = await dataResponse.json();
  rightPanel.render(extractedData.page_data.extracted_fields);
  
  // Update pagination UI
  pageCounter.textContent = `Page ${pageNumber} of ${totalPages}`;
}

// Navigation buttons
nextButton.onclick = () => loadPage(Math.min(currentPage + 1, totalPages));
prevButton.onclick = () => loadPage(Math.max(currentPage - 1, 1));
```

### React Example

```jsx
function SplitScreenEditor({ documentId, totalPages }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageImage, setPageImage] = useState(null);
  const [pageData, setPageData] = useState(null);
  
  useEffect(() => {
    async function loadPage() {
      const [imgRes, dataRes] = await Promise.all([
        fetch(`/api/documents/${documentId}/pages/${currentPage}/image`).then(r => r.json()),
        fetch(`/api/documents/${documentId}/pages/${currentPage}`).then(r => r.json())
      ]);
      setPageImage(imgRes.image_base64);
      setPageData(dataRes.page_data);
    }
    loadPage();
  }, [documentId, currentPage]);
  
  return (
    <div className="split-screen">
      {/* Left Panel - Original Image */}
      <div className="left-panel">
        {pageImage && <img src={`data:image/png;base64,${pageImage}`} alt={`Page ${currentPage}`} />}
        <div className="pagination">
          <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))}>Previous</button>
          <span>Page {currentPage} of {totalPages}</span>
          <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}>Next</button>
        </div>
      </div>
      
      {/* Right Panel - Extracted Data */}
      <div className="right-panel">
        <h2>Extracted Data</h2>
        {pageData?.extracted_fields?.map((field, i) => (
          <div key={i} className="field">
            <label>{field.key}:</label>
            <input defaultValue={field.value} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Key Synchronization Rules

| PDF Viewer Action | API Call | Result |
|------------------|----------|--------|
| User opens page 1 | `GET .../pages/1` | Show page 1 data |
| User clicks "Next" (now page 2) | `GET .../pages/2` | Show page 2 data |
| User jumps to page 5 | `GET .../pages/5` | Show page 5 data |
| User clicks "Previous" (now page 4) | `GET .../pages/4` | Show page 4 data |

**The `page_number` field is always 1-indexed and matches PDF page numbers exactly.**

---

## Error Handling

```javascript
async function loadPage(pageNumber) {
  try {
    const response = await fetch(`/api/documents/${documentId}/pages/${pageNumber}`);
    if (!response.ok) {
      if (response.status === 404) {
        showError("Page not found");
      } else if (response.status === 400) {
        showError("Invalid page number");
      }
      return;
    }
    // ... render page
  } catch (error) {
    showError("Network error");
  }
}
```

---

## Performance Tips

1. **Preload adjacent pages** - When user views page N, prefetch pages N-1 and N+1
2. **Use raw image format** for direct `<img src>` if your setup supports it
3. **Cache responses** - Page data won't change, so cache it client-side
4. **Lazy load** - Only fetch page data when user actually navigates to that page

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ocr/extract` | POST | Upload & process document, returns `document_id` |
| `/api/documents` | GET | List all stored documents |
| `/api/documents/{id}` | GET | Get full document with all pages |
| `/api/documents/{id}/pages/{n}/image` | GET | Get page N image (base64 or raw PNG) |
| `/api/documents/{id}/pages/{n}` | GET | Get extracted data for page N |
| `/api/documents/{id}` | DELETE | Delete stored document |
