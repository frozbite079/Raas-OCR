from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

JWT_SECRET = os.getenv("JWT_SECRET", "raas_jwt_secret_key")
security = HTTPBearer()

async def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

from models.schemas import (
    OCRResponse,
    ExtractionConfig,
    PageImageResponse,
    PageDataResponse,
    DocumentInfoResponse,
)
from services.ocr_service import OCRService
from services.document_store import document_store, DocumentStore
from services.html_template_service import html_template_service
from services.monitoring_service import tracker


def compact_html_for_json(html: Optional[str]) -> Optional[str]:
    if html is None:
        return None
    return html.replace("\r", "").replace("\n", "")


app = FastAPI(
    title="Raas-OCR API",
    description="OCR API for extracting handwritten data from electrical test reports using GPT-4o-mini",
    version="1.0.0",
)

# CORS: allow browser clients (local frontend/dev servers) to call this API.
cors_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = (
    [origin.strip() for origin in cors_allow_origins.split(",") if origin.strip()]
    if cors_allow_origins != "*"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR service
ocr_service = OCRService()

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)


@app.get("/")
async def root():
    """API Health Check"""
    return {
        "status": "running",
        "message": "Raas-OCR API is ready",
        "endpoints": {
            "extract": "POST /api/ocr/extract - Extract & store document (returns document_id)",
            "extract_html": "POST /api/ocr/extract-html - Extract first file and return text/html",
            "extract_with_keys": "POST /api/ocr/extract-with-keys - Extract specific fields",
            "get_page_image": "GET /api/documents/{doc_id}/pages/{page_num}/image - Get page image",
            "get_page_data": "GET /api/documents/{doc_id}/pages/{page_num} - Get extracted data for page",
            "get_page_html": "GET /api/documents/{doc_id}/pages/{page_num}/html - Get rendered page HTML",
            "list_documents": "GET /api/documents - List all stored documents",
            "docs": "GET /docs - API documentation",
        },
        "supported_formats": ["PDF (multi-page)", "PNG", "JPG", "JPEG"],
        "document_types": [
            "PT TEST REPORT",
            "CT TEST REPORT",
            "TEST CERTIFICATE OF NUMERICAL RELAY RMU",
            "RELEASE TEST REPORT",
            "CHECK - LIST OF MVS ACB/MCCB SERVICING",
            "TEST REPORT OF POSTAL TRANSFORMER",
            "TEST REPORT OF CURRENT TRANSFORMER",
            "TEST CERTIFICATE OF POWER TRANSFORMER",
            "TEST CERTIFICATE OF TRANSFORMER",
            "ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER)",
            "TEST CERTIFICATE OF AUXILIARY RELAY",
            "SERVICE REPORT FOR LV CIRCUIT BREAKER",
            "ACB CHECK LIST",
            "VCB MAINTENANCE CHECK LIST",
            "HT PANEL PREVENTIVE MAINTENANCE CHECKLIST",
            "TEST CERTIFICATE OF HT SWITCHGEAR PANEL",
            "SIEMENS RMU",
        ],
        "page_sync_guide": {
            "description": "For split-screen page synchronization:",
            "step1": "Upload document via POST /api/ocr/extract → get document_id",
            "step2": "Use document_id + page_number to fetch synchronized image and data",
            "step3": "When user navigates to page N, call both endpoints with page_num=N",
        },
    }


@app.post("/api/ocr/extract", response_model=OCRResponse, dependencies=[Depends(verify_jwt)])
async def extract_document(
    files: List[UploadFile] = File(...),
    document_type: Optional[str] = Form(None, description="Document type hint"),
    include_images: bool = Form(
        False, description="Include base64 page images in response"
    ),
    include_html: bool = Form(
        False, description="Include filled HTML templates in response"
    ),
):
    """
    Extract handwritten data from PDF or images and store for later retrieval.

    - **files**: Upload one or more PDF or image files (PDF, PNG, JPG, JPEG)
    - **document_type**: Optional - specify document type or leave empty for auto-detection
    - **include_images**: If True, includes base64 page images in response (larger payload)

    Returns JSON with extracted key-value pairs for each page, plus document_id for page sync.

    ## Page Synchronization
    Use the returned `document_id` to fetch individual pages:
    - `GET /api/documents/{document_id}/pages/{page_num}/image` - Get page image
    - `GET /api/documents/{document_id}/pages/{page_num}` - Get extracted data
    """
    try:
        result = await ocr_service.process_documents(
            files,
            document_type=document_type,
            store_pages=True,
            include_images=include_images,
            include_html=include_html,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ocr/extract-with-keys", response_model=OCRResponse, dependencies=[Depends(verify_jwt)])
async def extract_with_custom_keys(
    files: List[UploadFile] = File(...), keys: Optional[str] = None
):
    """
    Extract specific fields from documents.

    - **files**: Upload one or more PDF or image files
    - **keys**: Comma-separated list of field names to extract (e.g., "Client,Plant,Date,Remarks")

    Returns JSON with only the specified fields extracted.
    """
    try:
        key_list = [k.strip() for k in keys.split(",")] if keys else None
        result = await ocr_service.process_documents(
            files, extraction_keys=key_list, store_pages=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ocr/extract-html", dependencies=[Depends(verify_jwt)])
async def extract_document_html(
    files: List[UploadFile] = File(...),
    document_type: Optional[str] = Form(None, description="Document type hint"),
    template_ids: Optional[str] = Form(None, description="JSON list of allowed template IDs"),
    client_po_quota: Optional[str] = Form(
        None,
        description=(
            "JSON object with reportTypes array. Each entry has: "
            "type, quantity, used (optional), templateId (optional). "
            "Example: {\"reportTypes\": [{\"type\": \"PT Test Report\", "
            "\"quantity\": 10, \"used\": 3, \"templateId\": \"abc-123\"}]}"
        ),
    ),
):
    """
    Extract OCR and return only the first document's rendered HTML as text/html.

    **Quota enforcement (client_po_quota)**:
    - If a matching templateId entry has `quantity == 0` → 403 (not allowed).
    - If `used >= quantity` → 403 (quota exhausted).
    - If `used < quantity` → OCR proceeds normally.
    """
    import json

    # ------------------------------------------------------------------ #
    #  1. Parse template_ids (allowed list)                               #
    # ------------------------------------------------------------------ #
    allowed_template_ids: Optional[list] = None
    if template_ids:
        try:
            allowed_template_ids = json.loads(template_ids)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="template_ids must be a valid JSON array"
            )

    # ------------------------------------------------------------------ #
    #  2. Parse client_po_quota → build templateId → quota entry map     #
    # ------------------------------------------------------------------ #
    template_quota_map: dict = {}
    if client_po_quota:
        try:
            quota_data = json.loads(client_po_quota)
            if isinstance(quota_data, str):          # handle double-encoded JSON
                quota_data = json.loads(quota_data)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="client_po_quota must be a valid JSON object",
            )
        if not isinstance(quota_data, dict):
            raise HTTPException(
                status_code=400,
                detail="client_po_quota must decode to a JSON object",
            )
        template_quota_map = {
            entry["templateId"]: entry
            for entry in quota_data.get("reportTypes", [])
            if entry.get("templateId")
        }

    # ------------------------------------------------------------------ #
    #  3. AI detection — get doc type & templateId BEFORE full OCR       #
    # ------------------------------------------------------------------ #
    try:
        detected_type, detected_template_id = await ocr_service.detect_document_template(files[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document detection failed: {e}")

    # 3a. Unrecognised document type
    if detected_type == "OTHER" or not detected_template_id:
        return JSONResponse(
            status_code=400,
            content={
                "error": "wrong_template",
                "message": (
                    "Template not found for the uploaded document. "
                    "Please upload a valid report."
                ),
            },
        )

    # 3b. Check templateId is in the allowed list
    if allowed_template_ids is not None and detected_template_id not in allowed_template_ids:
        return JSONResponse(
            status_code=403,
            content={
                "error": "invalid_report",
                "message": (
                    f"Invalid report: '{detected_type}' is not permitted for this request."
                ),
            },
        )

    # 3c. Quota check
    if template_quota_map and detected_template_id in template_quota_map:
        quota_entry = template_quota_map[detected_template_id]
        quantity: int = int(quota_entry.get("quantity", 0))
        used: int     = int(quota_entry.get("used", 0))
        report_label: str = quota_entry.get("type", detected_template_id)

        if quantity == 0:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "quota_not_allowed",
                    "message": (
                        f"You are not allowed to process '{report_label}'. "
                        f"No quota has been assigned for this report type."
                    ),
                },
            )

        if used >= quantity:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "quota_exhausted",
                    "message": (
                        f"You have used all your quota for '{report_label}'. "
                        f"({used}/{quantity} reports used). "
                        f"Please contact your administrator to increase the quota."
                    ),
                },
            )
        # used < quantity → quota available ✅

    # ------------------------------------------------------------------ #
    #  4. Full OCR — pass detected_type so service skips re-detection    #
    # ------------------------------------------------------------------ #
    try:
        result = await ocr_service.process_documents(
            files=files,
            document_type=detected_type,       # already known → no 2nd AI call
            allowed_template_ids=None,         # permission already verified above
            store_pages=False,
            include_images=False,
            include_html=True,
        )
        if not result.documents:
            raise HTTPException(status_code=404, detail="No document data returned")

        first_doc = result.documents[0]

        # Propagate OCR-level errors (e.g. extraction failure)
        if first_doc.pages and first_doc.pages[0].title == "Error":
            error_msg = (
                first_doc.pages[0].extracted_fields[0].value
                if first_doc.pages[0].extracted_fields
                else "Unknown error"
            )
            raise HTTPException(status_code=500, detail=error_msg)

        html = first_doc.filled_html
        if not html:
            raise HTTPException(status_code=404, detail="No HTML content generated")

        # filled_html → sorted list of {"html": "..."} objects
        if isinstance(html, dict):
            body_data = [html[k] for k in sorted(html.keys(), key=lambda x: int(x))]
        elif isinstance(html, list):
            body_data = [{"html": page_html} for page_html in html]
        else:
            body_data = [{"html": html}]

        extracted_data = [page.model_dump(exclude_none=True) for page in first_doc.pages]

        # DEBUG: print raw extracted data
        print("\n" + "!" * 60)
        print("DEBUG: RAW EXTRACTED OCR JSON (Before HTML Mapping)")
        print(json.dumps(extracted_data, indent=2))
        print("!" * 60 + "\n")

        return JSONResponse(
            content={
                "status": 200,
                "body": body_data,
                "extra_param": extracted_data,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================================
# PAGE SYNCHRONIZATION ENDPOINTS
# ============================================


@app.get("/api/documents", dependencies=[Depends(verify_jwt)])
async def list_documents():
    """
    List all stored documents.

    Returns list of documents with their IDs, filenames, and page counts.
    """
    return {"documents": document_store.list_documents()}


@app.get("/api/documents/{document_id}", dependencies=[Depends(verify_jwt)])
async def get_document_info(document_id: str):
    """
    Get document metadata and all extracted data.

    Returns the full OCR extraction result for a stored document.
    """
    doc = document_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    return {
        "document_id": doc.document_id,
        "filename": doc.filename,
        "total_pages": doc.total_pages,
        "created_at": doc.created_at.isoformat(),
        "extracted_data": doc.extracted_data,
    }


@app.get("/api/documents/{document_id}/pages/{page_num}/image", dependencies=[Depends(verify_jwt)])
async def get_page_image(
    document_id: str,
    page_num: int,
    format: str = Query("base64", description="Response format: 'base64' or 'raw'"),
):
    """
    Get the original image for a specific page.

    - **document_id**: ID returned from /api/ocr/extract
    - **page_num**: Page number (1-indexed, matches PDF page numbers)
    - **format**: 'base64' returns JSON with base64 string, 'raw' returns PNG binary

    ## Usage for Page Sync
    When user navigates to page N in the PDF viewer on the left panel,
    call this endpoint with page_num=N to get the corresponding image.
    """
    doc = document_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    if page_num < 1 or page_num > doc.total_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid page number. Document has {doc.total_pages} pages (1-{doc.total_pages})",
        )

    image_bytes = doc.get_page_image(page_num)
    if not image_bytes:
        raise HTTPException(
            status_code=404, detail=f"Image not found for page {page_num}"
        )

    if format == "raw":
        return Response(content=image_bytes, media_type="image/png")

    # Default: base64 JSON response
    return PageImageResponse(
        document_id=document_id,
        page_number=page_num,
        total_pages=doc.total_pages,
        image_base64=doc.get_page_image_base64(page_num),
    )


@app.get(
    "/api/documents/{document_id}/pages/{page_num}", response_model=PageDataResponse, dependencies=[Depends(verify_jwt)]
)
async def get_page_data(
    document_id: str,
    page_num: int,
    include_html: bool = Query(
        False, description="Include filled HTML template in response"
    ),
):
    """
    Get extracted OCR data for a specific page.

    - **document_id**: ID returned from /api/ocr/extract
    - **page_num**: Page number (1-indexed, matches PDF page numbers)

    ## Usage for Page Sync
    When user navigates to page N in the PDF viewer on the left panel,
    call this endpoint with page_num=N to get the extracted data to display
    on the right panel.

    ## Synchronization Logic
    ```
    Left Panel (PDF Viewer): currentPage = 3
    Right Panel API Call:    GET /api/documents/{id}/pages/3
    Result:                  Display page_data.extracted_fields on right
    ```
    """
    doc = document_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    if page_num < 1 or page_num > doc.total_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid page number. Document has {doc.total_pages} pages (1-{doc.total_pages})",
        )

    page_data = doc.get_page_data(page_num)
    if not page_data:
        raise HTTPException(
            status_code=404, detail=f"Data not found for page {page_num}"
        )

    # Fill HTML template if requested
    filled_html = None
    if include_html and page_data.category:
        filled_html = html_template_service.process_document_html(
            page_data.category, [page_data]
        )
        filled_html = compact_html_for_json(filled_html)

    return PageDataResponse(
        document_id=document_id,
        page_number=page_num,
        total_pages=doc.total_pages,
        page_data=page_data,
        filled_html=filled_html,
    )


@app.get("/api/documents/{document_id}/pages/{page_num}/html", dependencies=[Depends(verify_jwt)])
async def get_page_html(document_id: str, page_num: int):
    """
    Return rendered HTML for a specific stored page as text/html.
    """
    doc = document_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    if page_num < 1 or page_num > doc.total_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid page number. Document has {doc.total_pages} pages (1-{doc.total_pages})",
        )

    page_data = doc.get_page_data(page_num)
    if not page_data:
        raise HTTPException(
            status_code=404, detail=f"Data not found for page {page_num}"
        )

    html = html_template_service.process_document_html(
        page_data.category or "OTHER", [page_data]
    )
    if not html:
        raise HTTPException(status_code=404, detail="No HTML content generated")
    return Response(content=html, media_type="text/html; charset=utf-8")


@app.delete("/api/documents/{document_id}", dependencies=[Depends(verify_jwt)])
async def delete_document(document_id: str):
    """Delete a stored document."""
    if document_store.delete_document(document_id):
        return {"message": f"Document {document_id} deleted"}
    raise HTTPException(status_code=404, detail=f"Document {document_id} not found")


# ============================================
# MONITORING ENDPOINTS
# ============================================


@app.get("/api/monitoring/stats", dependencies=[Depends(verify_jwt)])
async def monitoring_stats():
    """
    Get MLflow token usage statistics.

    Returns:
    - Current session stats (tokens & cost for the most recent OCR call)
    - All-time aggregated stats (total tokens, cost, breakdown by document type)
    - Link to the MLflow dashboard UI

    ## Launch Dashboard
    ```
    mlflow ui --host 0.0.0.0 --port 9000
    ```
    Then open http://localhost:9000 in your browser.
    """
    return {
        "current_session": tracker.get_session_stats(),
        "all_time":        tracker.get_all_time_stats(),
        "dashboard_hint": "Run: mlflow ui --host 0.0.0.0 --port 9000",
    }


@app.get("/api/monitoring/dashboard-url")
async def monitoring_dashboard_url():
    """Returns the MLflow dashboard URL (no auth required for easy access)."""
    return {
        "mlflow_ui": "http://localhost:9000",
        "command":   "mlflow ui --host 0.0.0.0 --port 9000",
        "note":      "Run the command above in the project directory to start the dashboard.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
