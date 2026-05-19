import os
import base64
import tempfile
from dotenv import load_dotenv

load_dotenv()

from typing import List, Optional, Tuple
from fastapi import UploadFile
from pdf2image import convert_from_bytes
from PIL import Image
import io
import json
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from services.document_store import document_store

from models.schemas import (
    OCRResponse,
    DocumentData,
    PageData,
    ExtractedField,
    DEFAULT_EXTRACTION_KEYS,
    DOCUMENT_TYPE_KEYS,
    DOCUMENT_PAGE_KEYS,
)
from services.html_template_service import html_template_service
from services.generic_html_generator import generate_generic_html
from services.monitoring_service import tracker


# All supported document types
DOCUMENT_TYPES = [
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
]

TEMPLATE_IDS = {
    "RELEASE TEST REPORT": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    "PT TEST REPORT": "c2d3e4f5-g6h7-4i8j-9k0l-1m2n3o4p5q6r",
    "TEST CERTIFICATE OF POWER TRANSFORMER": "d5c4b3a2-1e0f-4d3c-8b7a-9a8b7c6d5e4f",
    "TEST CERTIFICATE OF TRANSFORMER": "8cf63f17-8afb-4c97-8350-a157ee0c2e28",
    "TEST REPORT OF CURRENT TRANSFORMER": "e29ca76b-bc95-46c4-8fa3-aabb50222eec",
    "CT TEST REPORT": "e29ca76b-bc95-46c4-8fa3-aabb50222eec",
    "ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER)": "e3085e54-6440-42c1-a4d4-223169895bbe",
    "TEST CERTIFICATE OF NUMERICAL RELAY RMU": "e6f5d4c3-b2a1-0f1e-9d8c-7b6a5a4c3b2d",
    "TEST REPORT OF POSTAL TRANSFORMER": "f19ca76b-bc95-46c4-8fa3-aabb50222eed",
    "CHECK - LIST OF MVS ACB/MCCB SERVICING": "f7e6d5c4-b3a2-1f0e-9d8c-7b6a5a4c3b2e",
    "TEST CERTIFICATE OF AUXILIARY RELAY": "a7e6d5c4-b3a2-1f0e-9d8c-7b6a5a4c3b20",
    "SERVICE REPORT FOR LV CIRCUIT BREAKER": "4791ddd9-56ed-4376-9b2d-20fef1d0dda0",
    "ACB CHECK LIST": "c7e6d5c4-b3a2-1f0e-9d8c-7b6a5a4c3b22",
    "VCB MAINTENANCE CHECK LIST": "7761af31-6f6e-4052-87c3-ac4c83893eeb",
    "HT PANEL PREVENTIVE MAINTENANCE CHECKLIST": "44f33ffb-4d8b-4a1c-91fe-8ec992fb6059",
    "TEST CERTIFICATE OF HT SWITCHGEAR PANEL": "83d9cebd-43f0-4a0d-9a52-5b7ea8617124",
    "SIEMENS RMU": "2edf7566-9373-4a92-b114-c8def1189496",
}


class OCRService:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0, max_tokens=16384)
        #self.llm = ChatOpenAI(model="GLM-4.6V-Flash", temperature=0, max_tokens=16384,base_url="https://api.z.ai/api/paas/v4/",api_key="acf9490ad2234746b071fb492d2eb49a.9lYnlrjORzzPdefc")


    @staticmethod
    def _compact_html_for_json(html: str) -> str:
        """Return HTML as a single line for cleaner JSON payloads."""
        return html.replace("\r", "").replace("\n", "")

    @staticmethod
    def _normalize_extracted_value(value: object) -> str:
        """Normalize OCR values like '\\"asd\\"' or '"asd"' to plain text."""
        text = str(value).strip()
        text = text.replace('\\"', '"').replace("\\'", "'")
        while len(text) >= 2 and (
            (text[0] == '"' and text[-1] == '"')
            or (text[0] == "'" and text[-1] == "'")
        ):
            text = text[1:-1].strip()
        return text

    async def detect_document_template(
        self, file: UploadFile
    ) -> tuple:
        """
        Lightweight AI detection on the first page of the uploaded file.

        Returns:
            (doc_type: str, template_id: Optional[str])
            doc_type    — canonical document type string (e.g. "PT TEST REPORT")
                          or "OTHER" if unrecognised.
            template_id — the UUID from TEMPLATE_IDS, or None for OTHER/unknown.

        The file cursor is reset to position 0 after reading so the same
        UploadFile can be passed to process_documents() afterwards.
        """
        content = await file.read()
        await file.seek(0)  # reset so process_documents can re-read the file

        filename = (file.filename or "").lower()
        if filename.endswith(".pdf"):
            images = convert_from_bytes(content, dpi=150)  # low DPI — detection only
            if not images:
                return "OTHER", None
            img = self._resize_image_for_detection(images[0])
        else:
            img = Image.open(io.BytesIO(content))
            img = self._resize_image_for_detection(img)

        doc_type = await self._detect_document_type(img)
        template_id = (
            TEMPLATE_IDS.get(doc_type.upper())
            if doc_type and doc_type.upper() != "OTHER"
            else None
        )
        return doc_type, template_id

    async def process_documents(
        self,
        files: List[UploadFile],
        extraction_keys: Optional[List[str]] = None,
        document_type: Optional[str] = None,
        allowed_template_ids: Optional[List[str]] = None,
        store_pages: bool = False,
        include_images: bool = False,
        include_html: bool = False,
    ) -> OCRResponse:
        """
        Process multiple documents (PDFs or images).

        Args:
            files: List of uploaded files
            extraction_keys: Specific keys to extract
            document_type: Document type hint
            store_pages: If True, stores documents for later page-by-page retrieval
            include_images: If True, includes base64 images in the response
            include_html: If True, includes filled HTML templates in the response
        """

        documents = []

        for file in files:
            try:
                content = await file.read()
                filename = file.filename or "unknown"

                # ── Start MLflow monitoring session for this file ──
                tracker.start_session(
                    document_name=filename,
                    document_type=document_type,
                )

                if filename.lower().endswith(".pdf"):
                    doc_data, page_images = await self._process_pdf(
                        content,
                        filename,
                        extraction_keys,
                        document_type,
                        allowed_template_ids,
                        include_images,
                        include_html,
                    )
                else:
                    doc_data, page_images = await self._process_image(
                        content,
                        filename,
                        extraction_keys,
                        document_type,
                        allowed_template_ids,
                        include_images,
                        include_html,
                    )

                # Store document for page-by-page retrieval
                if store_pages and page_images:
                    doc_id = document_store.store_document(
                        filename=filename,
                        page_images=page_images,
                        extracted_data=doc_data,
                    )
                    doc_data.document_id = doc_id

                documents.append(doc_data)
                tracker.end_session()

            except Exception as e:
                tracker.end_session()  # always close session on error too
                documents.append(
                    DocumentData(
                        filename=file.filename or "unknown",
                        total_pages=0,
                        pages=[
                            PageData(
                                page_number=1,
                                title="Error",
                                extracted_fields=[
                                    ExtractedField(key="error", value=str(e))
                                ],
                            )
                        ],
                    )
                )

        from models.schemas import TokenStats

        # Get token stats from tracker
        stats = tracker.get_session_stats()
        usage_stats = TokenStats(
            input_tokens=stats["tokens"]["input"],
            output_tokens=stats["tokens"]["output"],
            total_tokens=stats["tokens"]["total"],
            estimated_cost_usd=stats["estimated_cost_usd"]
        )

        return OCRResponse(
            success=True,
            message=f"Processed {len(documents)} document(s)",
            documents=documents,
            summary=self._generate_summary(documents),
            include_html=include_html,
            usage=usage_stats,
        )

    async def _process_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        keys: Optional[List[str]] = None,
        doc_type: Optional[str] = None,
        allowed_template_ids: Optional[List[str]] = None,
        include_images: bool = False,
        include_html: bool = False,
    ) -> tuple[DocumentData, List[bytes]]:
        """
        Convert PDF to images and process each page.

        Returns:
            Tuple of (DocumentData, list of PNG bytes for each page)
        """

        # Convert PDF pages to images
        # Use lower DPI to reduce image size while maintaining readability
        images = convert_from_bytes(pdf_bytes, dpi=200)
        
        # Resize images to avoid exceeding API limits while maintaining OCR quality
        resized_images = []
        for img in images:
            resized_img = self._resize_image_for_ocr(img, max_size=1200)
            resized_images.append(resized_img)
        images = resized_images

        pages = []
        page_images = []
        detected_type = None
        use_type = None

        for i, img in enumerate(images):
            # Convert PIL image to PNG bytes for storage
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            png_bytes = buffered.getvalue()
            page_images.append(png_bytes)

            # For first page, detect document type if not specified
            if i == 0:
                if not doc_type:
                    detected_type = await self._detect_document_type(img)
                use_type = doc_type or detected_type
                
                # Check allowed template ids
                if allowed_template_ids is not None:
                    matched_template_id = TEMPLATE_IDS.get((use_type or "").upper())
                    if not matched_template_id or matched_template_id not in allowed_template_ids:
                        raise PermissionError(f"Permission denied: Document type '{use_type}' is not allowed.")

            # Use appropriate keys based on document type
            use_type = doc_type or detected_type
            if keys:
                use_keys = keys
            elif use_type and use_type in DOCUMENT_PAGE_KEYS:
                # Page-aware key selection: each page only sees the fields on that page
                page_key_list = DOCUMENT_PAGE_KEYS[use_type]
                # Use the last entry for overflow pages
                page_index = min(i, len(page_key_list) - 1)
                use_keys = page_key_list[page_index]
                print(f"[DEBUG] Page {i+1}: using page-specific keys ({len(use_keys)} keys) for '{use_type}'")
            elif use_type and use_type in DOCUMENT_TYPE_KEYS:
                use_keys = DOCUMENT_TYPE_KEYS[use_type]
            else:
                use_keys = DEFAULT_EXTRACTION_KEYS

            page_data = await self._extract_from_image(img, i + 1, use_keys, use_type)

            # Optionally include base64 image in response
            if include_images:
                page_data.page_image_base64 = base64.b64encode(png_bytes).decode(
                    "utf-8"
                )

            pages.append(page_data)

        doc_data = DocumentData(filename=filename, total_pages=len(images), pages=pages)

        # Fill HTML template if requested
        if include_html and len(pages) > 0:
            print(f"[DEBUG] Attempting to fill HTML for document type: {use_type}")

            # Try specific template first (only if use_type is not None)
            if use_type:
                filled_html = html_template_service.process_document_html(
                    use_type, pages
                )

                if filled_html:
                    if isinstance(filled_html, list):
                        doc_data.filled_html = {str(i): {"html": self._compact_html_for_json(h)} for i, h in enumerate(filled_html)}
                        print(f"[DEBUG] HTML filled successfully with multi-page template, lengths: {[len(h) for h in filled_html]}")
                    else:
                        doc_data.filled_html = {"0": {"html": self._compact_html_for_json(filled_html)}}
                        print(
                            f"[DEBUG] HTML filled successfully with template, length: {len(filled_html)}"
                        )
                else:
                    # Fallback to generic HTML
                    print(
                        f"[DEBUG] HTML template not found for type: {use_type}, using generic HTML"
                    )
                    doc_data.filled_html = {"0": {"html": self._compact_html_for_json(
                        generate_generic_html(pages[0])
                    )}}
                    print(
                        f"[DEBUG] Generic HTML generated, length: {len(doc_data.filled_html)}"
                    )
            else:
                # No document type detected, use generic HTML
                print(f"[DEBUG] No document type detected, using generic HTML")
                doc_data.filled_html = {"0": {"html": self._compact_html_for_json(
                    generate_generic_html(pages[0])
                )}}
                print(
                    f"[DEBUG] Generic HTML generated, length: {len(doc_data.filled_html)}"
                )

        return doc_data, page_images

    async def _process_image(
        self,
        image_bytes: bytes,
        filename: str,
        keys: Optional[List[str]] = None,
        doc_type: Optional[str] = None,
        allowed_template_ids: Optional[List[str]] = None,
        include_images: bool = False,
        include_html: bool = False,
    ) -> tuple[DocumentData, List[bytes]]:
        """
        Process a single image.

        Returns:
            Tuple of (DocumentData, list containing PNG bytes for the image)
        """

        img = Image.open(io.BytesIO(image_bytes))
        
        # Resize image to avoid exceeding API limits while maintaining OCR quality
        img = self._resize_image_for_ocr(img, max_size=1500)
        
        # Convert to PNG bytes for storage
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        png_bytes = buffered.getvalue()

        # Detect document type if not specified
        if not doc_type:
            doc_type = await self._detect_document_type(img)
            
        # Check allowed template ids
        if allowed_template_ids is not None:
            matched_template_id = TEMPLATE_IDS.get((doc_type or "").upper())
            if not matched_template_id or matched_template_id not in allowed_template_ids:
                raise PermissionError(f"Permission denied: Document type '{doc_type}' is not allowed.")

        # Use appropriate keys
        if keys:
            use_keys = keys
        elif doc_type and doc_type in DOCUMENT_TYPE_KEYS:
            use_keys = DOCUMENT_TYPE_KEYS[doc_type]
        else:
            use_keys = DEFAULT_EXTRACTION_KEYS

        page_data = await self._extract_from_image(img, 1, use_keys, doc_type)

        # Optionally include base64 image in response
        if include_images:
            page_data.page_image_base64 = base64.b64encode(png_bytes).decode("utf-8")

        doc_data = DocumentData(filename=filename, total_pages=1, pages=[page_data])

        # Fill HTML template if requested
        if include_html:
            print(f"[DEBUG] Image processing - document type: {doc_type}")

            # Try specific template first (only if doc_type is not None)
            if doc_type:
                filled_html = html_template_service.process_document_html(
                    doc_type, [page_data]
                )

                if filled_html:
                    if isinstance(filled_html, list):
                        doc_data.filled_html = {str(i): {"html": self._compact_html_for_json(h)} for i, h in enumerate(filled_html)}
                    else:
                        doc_data.filled_html = {"0": {"html": self._compact_html_for_json(filled_html)}}
                    print(
                        f"[DEBUG] HTML filled successfully with template, length: {len(filled_html)}"
                    )
                else:
                    # Fallback to generic HTML
                    print(
                        f"[DEBUG] HTML template not found for type: {doc_type}, using generic HTML"
                    )
                    doc_data.filled_html = {"0": {"html": self._compact_html_for_json(
                        generate_generic_html(page_data)
                    )}}
                    print(
                        f"[DEBUG] Generic HTML generated, length: {len(doc_data.filled_html)}"
                    )
            else:
                # No document type detected, use generic HTML
                print(f"[DEBUG] No document type detected, using generic HTML")
                doc_data.filled_html = {"0": {"html": self._compact_html_for_json(
                    generate_generic_html(page_data)
                )}}
                print(
                    f"[DEBUG] Generic HTML generated, length: {len(doc_data.filled_html)}"
                )

        return doc_data, [png_bytes]

    def _resize_image_for_detection(self, image: Image.Image, max_size: int = 1000) -> Image.Image:
        """Resize image to a smaller size to save tokens during detection."""
        w, h = image.size
        if max(w, h) <= max_size:
            return image
        
        if w > h:
            new_w = max_size
            new_h = int(h * (max_size / w))
        else:
            new_h = max_size
            new_w = int(w * (max_size / h))
            
        return image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def _resize_image_for_ocr(self, image: Image.Image, max_size: int = 1500) -> Image.Image:
        """Resize image to avoid exceeding API limits while maintaining OCR quality."""
        w, h = image.size
        if max(w, h) <= max_size:
            return image
        
        if w > h:
            new_w = max_size
            new_h = int(h * (max_size / w))
        else:
            new_h = max_size
            new_w = int(w * (max_size / h))
            
        return image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    async def _detect_document_type(self, image: Image.Image) -> str:
        """Detect the type of document from the image"""

        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        doc_types_list = "\n".join([f'- "{dt}"' for dt in DOCUMENT_TYPES])

        prompt = f"""Look at this document image and identify its type based on the title/heading.

Respond with ONLY ONE of these exact document type names:
{doc_types_list}
- "OTHER" if it doesn't match any of the above

Look at the title at the top of the document. Return the EXACT matching type name.
CRITICAL DISAMBIGUATION:
- If heading contains "MAINTENANCE CHECK LIST" or "MAINTENANCE CHECKLIST" with VCB, choose "VCB MAINTENANCE CHECK LIST".
- If heading contains "ROUTINE TEST CERTIFICATE" with VACUUM CIRCUIT BREAKER/VCB, choose "ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER)".
RESPOND WITH ONLY THE TYPE VALUE IN QUOTES, NOTHING ELSE."""

        # Resize image for detection to save tokens (Detection only needs to see the header)
        low_res_img = self._resize_image_for_detection(image)
        
        # Convert image to base64
        buffered = io.BytesIO()
        low_res_img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}",
                        "detail": "auto"  # Changed from low to auto so it respects the 1000px resize
                    },
                },
            ]
        )

        try:
            response = self.llm.invoke([message])
            tracker.log_llm_call(
                response,
                call_type="detection",
                document_type="auto-detect",
                model=self.llm.model_name,
            )
            doc_type = response.content.strip().replace('"', "").replace("'", "")

            def _normalize_type_text(text: str) -> str:
                return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()

            normalized_doc_type = _normalize_type_text(doc_type)
            normalized_type_map = {
                _normalize_type_text(dt): dt for dt in DOCUMENT_TYPES
            }

            # Exact canonical match first
            if normalized_doc_type in normalized_type_map:
                return normalized_type_map[normalized_doc_type]

            # Strong disambiguation between similarly named VCB forms
            if "vcb" in normalized_doc_type or "vacuum circuit breaker" in normalized_doc_type:
                if "maintenance" in normalized_doc_type and (
                    "check list" in normalized_doc_type or "checklist" in normalized_doc_type
                ):
                    return "VCB MAINTENANCE CHECK LIST"
                if "routine" in normalized_doc_type and "certificate" in normalized_doc_type:
                    return "ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER)"

            # Token-overlap fallback for near-miss model outputs
            response_tokens = set(normalized_doc_type.split())
            best_match = None
            best_score = 0.0
            for dt in DOCUMENT_TYPES:
                dt_tokens = set(_normalize_type_text(dt).split())
                if not dt_tokens:
                    continue
                score = len(response_tokens & dt_tokens) / len(dt_tokens)
                if score > best_score:
                    best_score = score
                    best_match = dt

            if best_match and best_score >= 0.6:
                return best_match

            return "OTHER"
        except Exception as e:
            print(f"Detection error: {e}")
            return "OTHER"

    async def _extract_from_image(
        self,
        image: Image.Image,
        page_num: int,
        keys: List[str],
        doc_type: Optional[str] = None,
    ) -> PageData:
        """Extract data from a single image using GPT-4o-mini"""

        # Resize image to a reasonable size to avoid exceeding API limits
        # while maintaining enough detail for OCR
        resized_image = self._resize_image_for_ocr(image, max_size=1500)
        
        # Convert image to base64 (use JPEG to reduce payload size)
        buffered = io.BytesIO()
        if resized_image.mode != 'RGB':
            resized_image = resized_image.convert('RGB')
        resized_image.save(buffered, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        # Build extraction prompt based on document type
        prompt = self._build_extraction_prompt(doc_type, keys)

        # Call GPT-4o-mini with vision
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}", "detail": "high"},
                },
            ]
        )

        try:
            response = self.llm.invoke([message])
            tracker.log_llm_call(
                response,
                call_type="extraction",
                document_type=doc_type,
                page_num=page_num,
                model=self.llm.model_name,
            )
            result = self._parse_llm_response(response.content)

            parsed_fields = []
            for f in result.get("fields", []):
                conf = f.get("confidence")
                # Try to safely parse confidence as a float
                try:
                    conf_val = float(conf) if conf is not None else 1.0
                except (ValueError, TypeError):
                    conf_val = 1.0
                
                # Only include confidence and explanation if score <= 0.85
                parsed_fields.append(
                    ExtractedField(
                        key=str(f.get("key", "")),
                        value=self._normalize_extracted_value(f.get("value", "")),
                        confidence=conf if conf_val <= 0.85 else None,
                        explanation=f.get("explanation") if conf_val <= 0.85 else None,
                    )
                )

            # Debug: Print all extracted fields for this page
            print(f"\n[DEBUG OCR PAGE {page_num}] Extracted {len(parsed_fields)} fields:")
            for pf in parsed_fields:
                print(f"  [PAGE {page_num}] '{pf.key}' => '{pf.value[:60] if pf.value else ''}'")
            print(f"[DEBUG OCR PAGE {page_num}] --- End of fields ---\n")

            category_val = str(result.get("category", doc_type) or "")
            report_type_val = category_val.replace(" ", "_").lower() if category_val else None
            report_id_val = TEMPLATE_IDS.get(category_val.upper())

            return PageData(
                page_number=page_num,
                title=result.get("title", doc_type),
                category=category_val,
                report_type=report_type_val,
                report_id=report_id_val,
                extracted_fields=parsed_fields,
            )
        except Exception as e:
            print(f"[ERROR] Extraction failed: {e}")
            return PageData(
                page_number=page_num,
                title="Extraction Error",
                extracted_fields=[ExtractedField(key="error", value=str(e))],
            )


    def _build_extraction_prompt(self, doc_type: Optional[str], keys: List[str]) -> str:
        """Build extraction prompt based on document type"""

        keys_str = "\n".join(
            [f"- {k}" for k in keys]
        )



        # Build Siemens Transformer Test Certificate guidance
        siemens_transformer_guidance = ""
        if doc_type and "TRANSFORMER" in doc_type.upper() and ("SIEMENS" in doc_type.upper() or "TEST CERTIFICATE" in doc_type.upper()):
            siemens_transformer_guidance = """

CRITICAL TABLE EXTRACTION RULES FOR SIEMENS TRANSFORMER TEST CERTIFICATE:

1. VOLTAGE RATIO TEST TABLE:
   Prefix the column names with 'VR '. e.g., "VR 1U1V", "VR 1V1W", "VR 1U1W", "VR 2U2V", "VR 2V2W", "VR 2U2W", "VR 2U2N", "VR 2V2N", "VR 2W2N".

2. VECTOR GROUP TABLE:
   Prefix with 'VG '. e.g., "VG 1U-2U", "VG 1V-2U", "VG 1W-2U", etc.

3. CONDITIONS TABLE:
   Prefix with 'Cond '. e.g., "Cond 1V2V = 1V2W", "Cond 1W2V > 1W2W", "Cond 1U2N + 1V2N = 1U1V".

4. MAGNETIC BALANCE TABLE (3 rows):
   This table has 3 value rows. You must specify the row number (R1, R2, R3).
   Keys MUST BE: "MB 1U1V R1", "MB 1V1W R1", "MB 1U1W R1", "MB 2U2N R1", "MB 2V2N R1", "MB 2W2N R1" for the first row.
   Use 'R2' for the second row, and 'R3' for the third row.

5. MAGNETISING CURRENT TABLE:
   Prefix with 'MC '. e.g., "MC U1", "MC V1", "MC W1".

6. WINDING RESISTANCE TABLE:
   - Look specifically for the section titled "WINDING RESISTANCE :".
   - It contains a column "TAP NO." (usually with row value "3").
   - The physical paper has a typo in the headers: "1U1V | 1V1W | 1V1W | 2U2N | 2V2N | 2W2N". The third column "1V1W" is actually "1U1W".
   - Extract the 6 handwritten values from this exact table row and map them to these 6 keys:
     "WR 1U1V", "WR 1V1W", "WR 1U1W", "WR 2U2N", "WR 2V2N", "WR 2W2N".
   - DO NOT pull values from the Insulation Resistance table into these keys.

7. INSULATION RESISTANCE TABLE:
   Keys are EXACTLY: "IR HT TO EARTH", "IR LT TO EARTH", "IR HT TO LT".
"""

        # Build VCB Maintenance Checklist guidance
        vcb_guidance = ""
        if doc_type and "VCB" in doc_type.upper() and ("MAINTENANCE" in doc_type.upper() or "CHECK" in doc_type.upper()):
            vcb_guidance = """

CRITICAL TABLE EXTRACTION RULES FOR VCB MAINTENANCE CHECK LIST:

1. SECTION 1.0 - TIMING TEST REPORT TABLE:
   3 columns: Phase | Closing Time | Tripping Time. Each row (R, Y, B) has 2 values.
   Use EXACT keys:
   Row R: "Timing R Closing Time", "Timing R Tripping Time"
   Row Y: "Timing Y Closing Time", "Timing Y Tripping Time"
   Row B: "Timing B Closing Time", "Timing B Tripping Time"

2. SECTION 2.0 - CONTACT RESISTANCE TABLE:
   Use EXACT keys: "Contact Resistance R Phase", "Contact Resistance Y Phase", "Contact Resistance B Phase"

3. SECTION 3.0 - VI DETAILS TABLE:
   2 rows, 3 columns (no headers).
   Row 1: "VI Details R Type", "VI Details Y Type", "VI Details B Type"
   Row 2: "VI Details R Serial", "VI Details Y Serial", "VI Details B Serial"

4. SECTION 4.0 - IR TEST TABLE (CRITICAL - 6 VALUE COLUMNS):
   This table has 3 COLUMN-PAIRS. Each pair has a label column and a value column.
   
   Pair 1: "Phase to Earth" labels (RE/YE/BE) with "Value in Ohm"
   Pair 2: "Phase to Phase" labels (RY/YB/BR) with "Value in Ohm"
   Pair 3: "Open Cond. Top-Bottom" labels (RR/YY/BB) with "Value in Ohm"
   
   Extract ALL 9 values using these EXACT keys:
   Row 1: "IR RE", "IR RY", "IR RR"
   Row 2: "IR YE", "IR YB", "IR YY"
   Row 3: "IR BE", "IR BR", "IR BB"
   
    WARNING: Do NOT skip the last column pair (Open Cond. Top-Bottom).
    The values next to RR, YY, BB MUST be extracted as "IR RR", "IR YY", "IR BB".
"""

        # Build Routine Test Certificate (VCB) guidance
        routine_vcb_guidance = ""
        if doc_type and "ROUTINE TEST CERTIFICATE" in doc_type.upper() and (
            "VACUUM CIRCUIT BREAKER" in doc_type.upper() or "VCB" in doc_type.upper()
        ):
            routine_vcb_guidance = """

CRITICAL EXTRACTION RULES FOR ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER):

1. HEADER ROW "RATED NORMAL CURRENT" + "VI-":
   - The "Rated Normal Current" row has two distinct handwritten value boxes.
   - Left value box maps ONLY to key: "Rated Normal Current".
   - Right small value box after label "VI-" maps ONLY to key: "VI-".
   - Never copy S/L No, Certificate No, VCB No, or any other header number into these two keys.

2. FIELD-BOUNDARY SAFETY:
   - Read each value from its own boxed cell only.
   - Do NOT borrow values from neighboring rows or columns even when handwriting overlaps lines.

3. RESISTANCE ROW SEPARATION:
   - The "Resistance" row has THREE separate value boxes, one under each of these labels:
     * "Closing Coil" -> Extract to key: "Closing Coil Ohm" (numeric value with Ω unit if visible)
     * "Tripping Coil" -> Extract to key: "Tripping Coil Ohm" (numeric value with Ω unit if visible)
     * "Motor" -> Extract to key: "Motor Ohm" (numeric value with Ω unit if visible)
   - Each resistance value is in its own boxed cell below its corresponding label.
   - Do NOT merge or copy values between these three cells.
   - If a cell appears blank or has "-", set the value to "-".

4. MANDATORY HEADER KEYS:
   - Always extract these keys if visible: "S/L NO", "Certificate No", "Customer", "WO No", "S/S Location", "Date", "Panel No", "VCB No", "Breaker Type", "Mechanism Type", "Feeder Name", "STC", "Counter Reading & Operation".
   - "Date" must come from the Date cell in the top-right header block only.
   - "Feeder Name" must come from the Feeder Name row only (do not use nearby values).
"""
        # Build Current Transformer Test Report guidance
        ct_guidance = ""
        if doc_type and ("CURRENT TRANSFORMER" in doc_type.upper() or "CT TEST REPORT" in doc_type.upper()):
            ct_guidance = """

CRITICAL HEADER TABLE EXTRACTION RULES FOR CURRENT TRANSFORMER TEST REPORT:

The header information table has a 2x4 grid layout:
- Row 1: [Label: "Client"] [Value field] [Label: "Tested DATE"] [Value field]
- Row 2: [Label: "Plant"] [Value field: "KV INDOOR PANEL"] [Label: "Tested By"] [Value field]  
- Row 3: [Label: "Location"] [Value field: "KV INDOOR PANEL"] [Empty] [Empty]

EXTRACTION ORDER - READ HORIZONTALLY LEFT-TO-RIGHT, ROW BY ROW:
1. Row 1, Left column: "Client" label -> extract handwritten value to key "Client"
2. Row 1, Right column: "Tested DATE" label -> extract date value to key "Tested DATE" (e.g., "26/05/26")
3. Row 2, Left column: "Plant" label -> extract value to key "Plant" (usually "KV INDOOR PANEL" or pre-filled)
4. Row 2, Right column: "Tested By" label -> extract person's name to key "Tested By" (handwritten name, not a date)
5. Row 3, Left column: "Location" label -> extract value to key "Location" (usually "KV INDOOR PANEL" or pre-filled)

CRITICAL ALIGNMENT RULES:
- Each label (Client, Plant, Location, Tested DATE, Tested By) is in a distinct cell.
- Each label has an input field or value directly to its right OR below it.
- DO NOT skip columns. DO NOT read diagonally across rows.
- The "Tested DATE" value MUST be a date (DD/MM/YY format or similar), NOT a plant/location name.
- The "Tested By" value MUST be a person's name (handwritten), NOT a date.
- Plant and Location values are often pre-printed as "KV INDOOR PANEL" or similar.
"""

        # Build HT Switchgear Panel guidance
        ht_switchgear_guidance = ""
        if doc_type and "HT SWITCHGEAR PANEL" in doc_type.upper():
            ht_switchgear_guidance = """

CRITICAL TABLE EXTRACTION RULES FOR HT SWITCHGEAR PANEL:

STEP 1 - FIND THE PRINTED COLUMN HEADERS:
There are TWO distinct tables. 
- 1.1 Metering Core is the TOP table.
- 1.2 Protection Core is the BOTTOM table.
Both tables have a printed header row. Headers left-to-right: Ph | Sr. No. | Ratio | VA | Acc. Class | Polarity | CT Resistance | Primary Injected Current A | Secondary Current | Meter Reading (Amp)

STEP 2 - MAP EACH CELL TO ITS HEADER:
For each row (R, Y, B), identify the cell directly BELOW each column header and extract the written value.
Do this for all 9 columns. Each column is separate. Do NOT merge adjacent columns.
Do NOT assume any value ranges. Read EXACTLY what is written in each cell.

WARNING - COLUMN MERGING PREVENTION:
The first 4 value columns (Sr. No., Ratio, VA, Acc. Class) all contain small 1-2 digit handwritten numbers written close together.
You MUST extract ALL FOUR as separate values. Do NOT merge or skip any.
- "Ratio" and "VA" are two separate columns. E.g., '11' and '14' -> Ratio=11, VA=14.
- "VA" and "Acc. Class" are also two separate columns. E.g., '14' and '18' -> VA=14, AccClass=18.

IMPORTANT: 'Acc. Class' is a SEPARATE column that sits between 'VA' and 'Polarity'. Do NOT skip it.

1. SECTION 1.1 - METERING CORE TABLE (TOP TABLE - 3 rows: R, Y, B):
   Row R: "Metering R Sr. No.", "Metering R Ratio", "Metering R VA", "Metering R Acc. Class", "Metering R Polarity", "Metering R CT Resistance", "Metering R Primary Injected Current", "Metering R Secondary Current", "Metering R Meter Reading"
   Row Y: "Metering Y Sr. No.", "Metering Y Ratio", "Metering Y VA", "Metering Y Acc. Class", "Metering Y Polarity", "Metering Y CT Resistance", "Metering Y Primary Injected Current", "Metering Y Secondary Current", "Metering Y Meter Reading"
   Row B: "Metering B Sr. No.", "Metering B Ratio", "Metering B VA", "Metering B Acc. Class", "Metering B Polarity", "Metering B CT Resistance", "Metering B Primary Injected Current", "Metering B Secondary Current", "Metering B Meter Reading"

2. SECTION 1.2 - PROTECTION CORE TABLE (BOTTOM TABLE - 3 rows: R, Y, B):
   Row R: "Protection R Sr. No.", "Protection R Ratio", "Protection R VA", "Protection R Acc. Class", "Protection R Polarity", "Protection R CT Resistance", "Protection R Primary Injected Current", "Protection R Secondary Current", "Protection R Meter Reading"
   Row Y: "Protection Y Sr. No.", "Protection Y Ratio", "Protection Y VA", "Protection Y Acc. Class", "Protection Y Polarity", "Protection Y CT Resistance", "Protection Y Primary Injected Current", "Protection Y Secondary Current", "Protection Y Meter Reading"
   Row B: "Protection B Sr. No.", "Protection B Ratio", "Protection B VA", "Protection B Acc. Class", "Protection B Polarity", "Protection B CT Resistance", "Protection B Primary Injected Current", "Protection B Secondary Current", "Protection B Meter Reading"
"""

        # Build ACB/MCCB checklist guidance
        acb_mccb_checklist_guidance = ""
        if doc_type and "CHECK - LIST OF MVS ACB/MCCB SERVICING" in doc_type.upper():
            acb_mccb_checklist_guidance = """

CRITICAL EXTRACTION RULES FOR CHECK - LIST OF MVS ACB/MCCB SERVICING:

1. TITLE REFERENCE BOX (UNDER MAIN TITLE):
   - There is a standalone rectangular box directly below the title.
   - Extract the handwritten identifier in this box to key: "Document Reference".
   - Example pattern: "B-9532" (alphanumeric with hyphen).
   - Do NOT map this value to Frame, Rating, or Sr. No.

2. HEADER GRID MAPPING (TOP TABLE):
   - Left column keys: "Frame", "Rating", "Sr. No."
   - Right column keys: "Accessories (Fitted)", "Location", "Date"
   - Keep row alignment strict; do not shift values between rows.

3. DATE FIELD:
   - Extract handwritten date (e.g., "26/11/2026") only into "Date".
   - Do not place date into title reference or checklist report rows.
"""

        # Build HT Panel IR Test guidance (used when page keys are IR-only)
        ht_panel_ir_guidance = ""
        if doc_type and "HT PANEL PREVENTIVE MAINTENANCE" in doc_type.upper():
            # Check if this is page 2 (only IR keys in use_keys)
            ir_keys = {"PM Before R-E", "PM Before R-Y", "PM After R-E", "PM After R-Y"}
            if ir_keys.issubset(set(keys)):
                ht_panel_ir_guidance = """

CRITICAL EXTRACTION RULES FOR HT PANEL INSULATION RESISTANCE TEST PAGE:

This page has TWO tables: "1.0 PM BEFORE" and "2.0 PM AFTER" insulation resistance test.

EACH TABLE HAS TWO ROWS:
  ROW 1 (Phase-to-Earth): R-E | [value] | Y-E | [value] | B-E | [value] | N-E | [value]
  ROW 2 (Phase-to-Phase): R-Y | [value] | Y-B | [value] | B-R | [value]

You MUST read BOTH rows for BOTH tables. Do NOT stop after row 1.

EXACT KEY MAPPING:
  Table 1.0 PM BEFORE:
    Row 1: "PM Before R-E", "PM Before Y-E", "PM Before B-E", "PM Before N-E"
    Row 2: "PM Before R-Y", "PM Before Y-B", "PM Before B-R"

  Table 2.0 PM AFTER:
    Row 1: "PM After R-E", "PM After Y-E", "PM After B-E", "PM After N-E"
    Row 2: "PM After R-Y", "PM After Y-B", "PM After B-R"

If a cell shows "-" or is blank, output the value as "-".
Extract ONLY the numeric value (or "-") — do NOT include units like MΩ or GΩ.

Critical:-try to fetch all fields values dont miss any!
"""

        # Build SIEMENS RMU guidance
        siemens_rmu_guidance = ""
        if doc_type and "SIEMENS RMU" in doc_type.upper():
            siemens_rmu_guidance = """

CRITICAL EXTRACTION RULES FOR SIEMENS RMU SERVICE REPORT:

1. HEADER INFORMATION TABLE (TOP GRID):
   This table is a 2-column grid: [Label] | [Value] | [Label] | [Value].
   Row 1: "CLINT" -> "Client" | "VOLTEGE" -> "Voltage"
   Row 2: "LOCATION" -> "Location" | "RATING" -> "Rating"
   Row 3: "PANAL NO." -> "Panel No." | "RELAY" -> "Relay"
   Row 4: "S/S No." -> "S/S No." | "SR No." -> "SR No."
   Row 5: "SWBD" -> "SWBD" | "TYPE" -> "Type"
   Row 6: "DATE" -> "Date" | "SERVICED BY" -> "Serviced By"
 
   IMPORTANT: 
   - Extract "PANAL NO.", "S/S No.", and "SWBD" with absolute precision.
   - Read BOTH columns carefully. Do NOT skip the right-side values (Relay, SR No, Type).

2. CHECK POINTS DESCRIPTION TABLE (Sr. No. 1 to 16):
   Each row has a "Status" and "Remarks" column.
   Extract both! 
   Key format: "[Number] [Description] Status" and "[Number] [Description] Remarks".
   E.g., "1 Visual inspection of RMU Status", "1 Visual inspection of RMU Remarks".
   
   Handwritten values are usually qualitative words like: nice, Good, Great, okay, ok.
   Read the EXACT word written in each cell.

3. INSULATION RESISTANCE TABLE (ITEM 17):
   3 columns (R, Y, B).
   Row 1: "IR Check R", "IR Check Y", "IR Check B"
   Row 2 (Phase to Phase): "IR Phase to Phase R", "IR Phase to Phase Y", "IR Phase to Phase B"
   Row 3 (Phase to Earth): "IR Phase to Earth R", "IR Phase to Earth Y", "IR Phase to Earth B"

4. CT DETAILS TABLE (BOTTOM):
   Standard 9-column table. Extract ALL columns for R, Y, B phases.
   Keys: "CT [Phase] Sr. No.", "CT [Phase] Ratio", "CT [Phase] VA", "CT [Phase] Class", "CT [Phase] Polarity", "CT [Phase] Primary Current", "CT [Phase] Secondary Current", "CT [Phase] Resistance".
"""

        # Build LV Circuit Breaker guidance (Now handled dynamically via data-hints in HTML)
        lv_breaker_guidance = ""

        # Build DYNAMIC guidance from the HTML template itself
        # Reads data-field attributes + printed labels to generate exact extraction rules
        dynamic_guidance = ""
        if doc_type:
            try:
                dynamic_guidance = html_template_service.extract_template_guidance(doc_type)
                if dynamic_guidance:
                    print(f"[DEBUG] Generated dynamic template guidance for '{doc_type}' ({len(dynamic_guidance)} chars)")
            except Exception as e:
                print(f"[DEBUG] Dynamic guidance generation failed: {e}")

        # Combine all guidance
        full_guidance = (
            siemens_transformer_guidance 
            + vcb_guidance 
            + routine_vcb_guidance
            + ct_guidance
            + acb_mccb_checklist_guidance
            + ht_switchgear_guidance 
            + ht_panel_ir_guidance
            + siemens_rmu_guidance
        )

        return f"""Analyze this electrical test report document and extract ALL handwritten/filled values.

DOCUMENT TYPE: {doc_type or "Auto-detect from title"}

TASK 1 - IDENTIFY THE TITLE:
Find the main title/heading of this document (usually at the top).

TASK 2 - EXTRACT ALL FIELDS:
Look for these fields and extract their handwritten/printed values:
{keys_str}
{full_guidance}
{lv_breaker_guidance}
{dynamic_guidance}
EXTRACTION RULES:
1. Extract EVERY value you can read from the document.
2. For tables, extract each cell value carefully. Align values strictly with their column headers. 
   STRICT COLUMN INDEPENDENCE: Never concatenate or merge text from two different vertical columns into a single value, even if the handwriting is very close together or overlaps the column boundary.
3. For checkboxes/tick marks, indicate "Yes", "No", "Checked", "OK" etc.
4. If a field is empty or not visible, return "" (empty string). Do NOT skip any keys from the provided list. Do NOT fabricate values.
5. Include units where applicable (e.g., "5 KV", "100 μΩ").
6. STRICT CONFIDENCE SCORING (0.0 to 1.0): Be extremely harsh.
   - 0.95-1.0: Perfect machine-printed text. No handwriting.
   - 0.80-0.94: Exceptionally clear and flawless block handwriting.
   - 0.60-0.79: Typical messy cursive, overlapping lines, or smudged ink.
   - 0.10-0.59: Barely legible, scribbles, ambiguous letters/numbers.
7. DETAILED EXPLANATION: You MUST explicitly state if the text is "Printed" or "Handwritten". Detail specific visual defects (e.g., "Handwritten, ink is faded, '5' looks like 'S'").

RESPOND IN THIS EXACT JSON FORMAT:
{{
    "title": "Document title as shown",
    "category": "{doc_type or "detected_type"}",
    "fields": [
        {{"key": "Field Name", "value": "extracted value", "confidence": 0.99, "explanation": "Printed text, perfectly clear"}},
        {{"key": "Another Field", "value": "its value", "confidence": 0.65, "explanation": "Handwritten cursive, overlapping the boundary box, slightly smudged"}},
        ...
    ]
}}
Critical rule :- if values pattern are mismatching dont ignore it for "HT PANEL PREVENTIVE MAINTENANCE CHECKLIST" data
IMPORTANT: Only return valid JSON. Extract as many fields as possible."""

    def _parse_llm_response(self, content: str) -> dict:
        """Parse JSON from LLM response"""

        # Clean up the response
        content = content.strip()

        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return {
                "title": "Parse Error",
                "category": "other",
                "fields": [{"key": "raw_response", "value": content[:500]}],
            }

    def _generate_summary(self, documents: List[DocumentData]) -> dict:
        """Generate summary of all extracted data"""

        total_pages = sum(d.total_pages for d in documents)
        all_fields = {}
        categories = {}

        for doc in documents:
            for page in doc.pages:
                # Count categories
                cat = page.category or "other"
                categories[cat] = categories.get(cat, 0) + 1

                # Aggregate fields
                for field in page.extracted_fields:
                    if field.key not in all_fields:
                        all_fields[field.key] = []
                    all_fields[field.key].append(
                        {
                            "value": field.value,
                            "source": f"{doc.filename} - Page {page.page_number}",
                        }
                    )

        return {
            "total_documents": len(documents),
            "total_pages": total_pages,
            "categories_found": categories,
            "fields_extracted": list(all_fields.keys()),
            "aggregated_data": all_fields,
        }
