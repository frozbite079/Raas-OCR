"""
HTML Template Service
Handles loading HTML templates and filling them with OCR data.
"""

import os
import html
from typing import Dict, List, Optional, Union
import re
from difflib import get_close_matches
from bs4 import BeautifulSoup
from models.schemas import PageData, DOCUMENT_TYPE_KEYS


# Document type to HTML file mapping
DOCUMENT_HTML_MAPPING = {
    "TEST CERTIFICATE OF POWER TRANSFORMER": "test_certificate_power_transformer.html",
    "POWER TRANSFORMER TEST CERTIFICATE": "test_certificate_power_transformer.html",
    "TEST CERTIFICATE OF TRANSFORMER": "siemens/test_certificate_of_transformer.html",
    "TEST CERTIFICATE OF NUMERICAL RELAY RMU": "test_certificate_of_numerical_relay_rmu.html",
    "CHECK - LIST OF MVS ACB/MCCB SERVICING": "checklist_mvs_acb_mccb.html",
    "PT TEST REPORT": "pt_test_report.html",
    "TEST REPORT OF POSTAL TRANSFORMER": "postal_transformer_test_report.html",
    "RELEASE TEST REPORT": "release_test_report.html",
    "ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER)": "routine_test_certificate.html",
    "TEST CERTIFICATE OF AUXILIARY RELAY": "test_certificate_auxiliary_relay.html",
    "SERVICE REPORT FOR LV CIRCUIT BREAKER": "siemens/service_report_for_lv_circuit_breaker.html",
    "ACB CHECK LIST": "siemens_acb_checklist.html",
    "VCB MAINTENANCE CHECK LIST": "vcb_maintenance_check_list.html",
    "VCB (VACUUM CIRCUIT BREAKER) MAINTENANCE CHECK LIST": "vcb_maintenance_check_list.html",
    "HT PANEL PREVENTIVE MAINTENANCE CHECKLIST": "ht_panel_preventive_maintenance.html",
    "TEST CERTIFICATE OF HT SWITCHGEAR PANEL": "siemens/test_certificate_of_ht_switchgear_panel.html",
    "SIEMENS RMU": "siemens/siemens_rmu.html",
    # Current Transformer Test Report — 2-page document handled in process_document_html
    "CT TEST REPORT": "current_transformer_test_report.html",
    "TEST REPORT OF CURRENT TRANSFORMER": "current_transformer_test_report.html",
}


class HTMLTemplateService:
    """Service for filling HTML templates with OCR data"""

    def __init__(self, html_dir: str = "html_pages"):
        self.html_dir = html_dir

    @staticmethod
    def _normalize_field_value(value: str) -> str:
        text = str(value).strip()
        text = text.replace('\\"', '"').replace("\\'", "'")
        while len(text) >= 2 and (
            (text[0] == '"' and text[-1] == '"')
            or (text[0] == "'" and text[-1] == "'")
        ):
            text = text[1:-1].strip()
        return text

    @staticmethod
    def _normalize_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()

    @staticmethod
    def _coerce_qualitative_value(value: str, allowed_values: set[str]) -> Optional[str]:
        """
        Try to coerce OCR-variant qualitative text to one of the allowed values.
        Returns a normalized allowed value when matched, else None.
        """
        if not value:
            return None

        raw = str(value).strip()
        if not raw:
            return None

        # Build normalized lookup map for allowed values
        allowed_lookup: Dict[str, str] = {}
        for item in allowed_values:
            item_text = str(item).strip()
            if not item_text:
                continue
            normalized = re.sub(r"[^a-z0-9]+", "", item_text.lower().rstrip("."))
            if normalized:
                allowed_lookup[normalized] = item_text

        candidate = re.sub(r"[^a-z0-9]+", "", raw.lower().rstrip("."))
        if not candidate:
            return None

        if candidate in allowed_lookup:
            return allowed_lookup[candidate]

        # Common OCR-ish confusions
        aliases = {
            "oky": "okay",
            "oka": "okay",
            "okai": "okay",
            "g00d": "good",
            "goood": "good",
            "perfecf": "perfect",
            "perfact": "perfect",
            "nce": "nice",
            "gr8": "great",
        }
        alias = aliases.get(candidate)
        if alias:
            alias_key = re.sub(r"[^a-z0-9]+", "", alias)
            if alias_key in allowed_lookup:
                return allowed_lookup[alias_key]

        # Fuzzy fallback
        nearest = get_close_matches(candidate, list(allowed_lookup.keys()), n=1, cutoff=0.78)
        if nearest:
            return allowed_lookup[nearest[0]]

        return None

    def _find_best_field_value(
        self, field_map: Dict[str, str], candidates: List[str]
    ) -> Optional[str]:
        normalized_field_map = {
            self._normalize_key(k): v for k, v in field_map.items() if k and v
        }

        # Exact normalized candidate match
        for candidate in candidates:
            nc = self._normalize_key(candidate)
            if nc in normalized_field_map:
                return normalized_field_map[nc]

        # Partial match fallback
        for candidate in candidates:
            nc = self._normalize_key(candidate)
            for nk, value in normalized_field_map.items():
                if nc and (nc in nk or nk in nc):
                    return value
        return None

    def _fill_postal_transformer_template(
        self, html_content: str, field_map: Dict[str, str]
    ) -> str:
        """
        Fill postal transformer template using deterministic field-to-cell mapping.
        This avoids row/column drift from naive sequential filling.
        """
        soup = BeautifulSoup(html_content, "lxml")
        editable_nodes = soup.select('[contenteditable="true"]')

        ordered_field_candidates: List[List[str]] = [
            ["Client"],
            ["Plant"],
            ["Tested DATE", "Date", "Tested On"],
            ["Location"],
            ["Feeder Name", "Feeder"],
            ["Phase R Make", "Make"],
            ["Phase R PT Ratio", "PT Ratio"],
            ["Phase R Sr. No", "Sr. No"],
            ["Phase R VA Core 1"],
            ["Phase R VA Core 2"],
            ["Phase R Accuracy Class Core 1"],
            ["Phase R Accuracy Class Core 2"],
            ["Phase Y Make"],
            ["Phase Y PT Ratio"],
            ["Phase Y Sr. No"],
            ["Phase Y VA Core 1"],
            ["Phase Y VA Core 2"],
            ["Phase Y Accuracy Class Core 1"],
            ["Phase Y Accuracy Class Core 2"],
            ["Phase B Make"],
            ["Phase B PT Ratio"],
            ["Phase B Sr. No"],
            ["Phase B VA Core 1"],
            ["Phase B VA Core 2"],
            ["Phase B Accuracy Class Core 1"],
            ["Phase B Accuracy Class Core 2"],
            ["Core1 Metering R Primary Voltage"],
            ["Core1 Metering R Secondary Voltage"],
            ["Core1 Metering R Secondary Winding Resistance"],
            ["Core1 Metering R Ratio"],
            ["Core1 Metering R Voltage Measured at Meter"],
            ["Core1 Metering Y Primary Voltage"],
            ["Core1 Metering Y Secondary Voltage"],
            ["Core1 Metering Y Secondary Winding Resistance"],
            ["Core1 Metering Y Ratio"],
            ["Core1 Metering Y Voltage Measured at Meter"],
            ["Core1 Metering B Primary Voltage"],
            ["Core1 Metering B Secondary Voltage"],
            ["Core1 Metering B Secondary Winding Resistance"],
            ["Core1 Metering B Ratio"],
            ["Core1 Metering B Voltage Measured at Meter"],
            ["Core2 Protection R Primary Voltage"],
            ["Core2 Protection R Secondary Voltage"],
            ["Core2 Protection R Secondary Winding Resistance"],
            ["Core2 Protection R Ratio"],
            ["Core2 Protection R Voltage Measured at Relay"],
            ["Core2 Protection Y Primary Voltage"],
            ["Core2 Protection Y Secondary Voltage"],
            ["Core2 Protection Y Secondary Winding Resistance"],
            ["Core2 Protection Y Ratio"],
            ["Core2 Protection Y Voltage Measured at Relay"],
            ["Core2 Protection B Primary Voltage"],
            ["Core2 Protection B Secondary Voltage"],
            ["Core2 Protection B Secondary Winding Resistance"],
            ["Core2 Protection B Ratio"],
            ["Core2 Protection B Voltage Measured at Relay"],
            ["IR Primary to Earth Measured Value"],
            ["IR Primary to Core 1 Measured Value"],
            ["IR Primary to Core 2 Measured Value"],
            ["IR Core 1 to Core 2 Measured Value"],
            ["IR Core 1 to Earth Measured Value"],
            ["IR Core 2 to Earth Measured Value"],
            ["General Check-up"],
            ["Continuity Checked & Found Proper"],
            ["Remark", "Remarks"],
        ]

        filled_count = 0
        for idx, node in enumerate(editable_nodes):
            if idx >= len(ordered_field_candidates):
                break
            value = self._find_best_field_value(field_map, ordered_field_candidates[idx])
            if value:
                node.string = str(value)
                filled_count += 1

        print(
            f"[DEBUG] Postal template deterministic fill count: {filled_count}/{len(editable_nodes)}"
        )
        return str(soup)

    def get_html_file(self, document_type: str) -> Optional[str]:
        """
        Get HTML filename for a given document type.

        Args:
            document_type: Type of document (e.g., "TEST CERTIFICATE OF POWER TRANSFORMER")

        Returns:
            HTML filename or None if not found
        """
        html_file = DOCUMENT_HTML_MAPPING.get(document_type)
        print(f"[DEBUG] get_html_file({document_type}) -> {html_file}")
        return html_file

    def load_template(self, html_file: str) -> Optional[str]:
        """
        Load HTML template from file.

        Args:
            html_file: Name of HTML file

        Returns:
            HTML content as string or None if file not found
        """
        filepath = os.path.join(self.html_dir, html_file)
        if not os.path.exists(filepath):
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Auto-sanitize: remove print buttons and unnecessary UI elements
        return self._sanitize_template(html_content)

    @staticmethod
    def _sanitize_template(html_content: str) -> str:
        """
        Strip print buttons, floating UI elements, and onclick scripts
        from HTML templates. These are useful in browsers but must be
        removed before OCR pipeline injection.
        """
        soup = BeautifulSoup(html_content, "lxml")

        # Remove all elements with class containing 'btn-print' or 'print'
        for btn in soup.select('.btn-print, [onclick*="print"]'):
            btn.decompose()

        # Remove CSS rules targeting .btn-print from <style> tags
        for style_tag in soup.find_all("style"):
            if style_tag.string:
                # Remove .btn-print { ... } blocks
                cleaned = re.sub(
                    r'\.btn-print\s*\{[^}]*\}', '', style_tag.string
                )
                style_tag.string = cleaned

        return str(soup)

    def fill_template_with_data(
        self, html_content: str, pages: List[PageData], document_type: Optional[str] = None
    ) -> str:
        """
        Fill HTML template with OCR extracted data from ALL pages.
        Uses data-field attributes on <input> elements for precise matching.
        Falls back to sequential filling for inputs without data-field attributes.

        Args:
            html_content: HTML template content
            pages: List of extracted OCR page data (all pages merged)

        Returns:
            Filled HTML content
        """

        # Merge fields from ALL pages into a single map (case-insensitive)
        # Later pages can override earlier ones if same key appears
        field_map = {}
        for page in pages:
            for field in page.extracted_fields:
                key = field.key.lower().strip()
                value = self._normalize_field_value(field.value)
                # Only set if value is non-empty (don't overwrite good data with blanks)
                if value:
                    field_map[key] = value

        if document_type == "ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER)":
            def _find_value_by_candidates(candidates: List[str]) -> Optional[str]:
                normalized_candidates = [self._normalize_key(c) for c in candidates if c]

                # Exact (raw) key match
                for candidate in candidates:
                    raw = str(candidate).lower().strip()
                    if raw in field_map and field_map[raw]:
                        return field_map[raw]

                # Exact normalized key match
                for key, value in field_map.items():
                    nk = self._normalize_key(key)
                    if nk in normalized_candidates and value:
                        return value

                # Partial normalized fallback
                for key, value in field_map.items():
                    nk = self._normalize_key(key)
                    for nc in normalized_candidates:
                        if nc and (nc in nk or nk in nc):
                            if value:
                                return value
                return None

            if not field_map.get("date"):
                recovered_date = _find_value_by_candidates(
                    ["Date", "Tested Date", "Inspection Date"]
                )
                if recovered_date:
                    field_map["date"] = recovered_date
                    print(f"[DEBUG BACKFILL] 'date' => '{recovered_date}'")

            if not field_map.get("feeder name"):
                recovered_feeder = _find_value_by_candidates(
                    ["Feeder Name", "Feeder", "Feeder Name:"]
                )
                if recovered_feeder:
                    field_map["feeder name"] = recovered_feeder
                    print(f"[DEBUG BACKFILL] 'feeder name' => '{recovered_feeder}'")

        # Field map was built here
        print(f"[DEBUG] Merged {len(field_map)} fields from {len(pages)} pages")
        # Debug: Print all extracted field keys
        for k, v in field_map.items():
            print(f"[DEBUG FIELD_MAP] '{k}' => '{v[:80] if v else ''}'")

        # Get list of field values in schema order (important for exact sequential alignment)
        field_values = []
        if document_type in DOCUMENT_TYPE_KEYS:
            for schema_key in DOCUMENT_TYPE_KEYS[document_type]:
                normalized_key = schema_key.lower().strip()
                # Try exact match first
                if normalized_key in field_map:
                    field_values.append(field_map[normalized_key])
                else:
                    # Try partial match if exact match fails
                    found_val = ""
                    for fm_key, fm_val in field_map.items():
                        if normalized_key in fm_key or fm_key in normalized_key:
                            found_val = fm_val
                            break
                    field_values.append(found_val)
        else:
            field_values = list(field_map.values())
            
        current_value_index = 0
        strict_data_field_only = document_type in {
            "SERVICE REPORT FOR LV CIRCUIT BREAKER",
            "TEST CERTIFICATE OF NUMERICAL RELAY RMU",
            "ROUTINE TEST CERTIFICATE (VACUUM CIRCUIT BREAKER)",
            "CHECK - LIST OF MVS ACB/MCCB SERVICING",
        }

        filled_count_data_field = 0
        filled_count_sequential = 0
        filled_count_contenteditable = 0

        def normalize_key(text: str) -> str:
            return self._normalize_key(text)

        def match_value_by_label(label: str) -> Optional[str]:
            """Try exact/partial key matching against extracted field keys."""
            if not label:
                return None
            nl = normalize_key(label)
            if not nl:
                return None
            compact_label = re.sub(r"[^a-z0-9]+", "", label.lower())

            # Exact normalized match first
            for key, value in field_map.items():
                if normalize_key(key) == nl:
                    return value

            # Exact compact match (helps y-b vs yb variants)
            for key, value in field_map.items():
                compact_key = re.sub(r"[^a-z0-9]+", "", str(key).lower())
                if compact_key and compact_key == compact_label:
                    return value

            # Then partial containment
            for key, value in field_map.items():
                nk = normalize_key(key)
                if nl in nk or nk in nl:
                    return value

            # Compact partial containment fallback
            for key, value in field_map.items():
                compact_key = re.sub(r"[^a-z0-9]+", "", str(key).lower())
                if compact_key and (
                    compact_label in compact_key or compact_key in compact_label
                ):
                    return value
            return None

        if document_type == "TEST REPORT OF POSTAL TRANSFORMER":
            return self._fill_postal_transformer_template(html_content, field_map)

        def replace_input_with_data_field(match):
            nonlocal filled_count_data_field
            full_tag = match.group(0)
            data_field = html.unescape(match.group(1)).lower().strip()

            if not data_field:
                return full_tag

            val_to_inject = None

            # 1. Exact match (lowered keys)
            if data_field in field_map:
                val_to_inject = field_map[data_field]
            else:
                # 2. Check for indexed field (e.g., "closing time (ms) 1" -> base "closing time (ms)" + index)
                index_match = re.search(r'(.*?)\s+(\d+)$', data_field)
                if index_match:
                    base_field = index_match.group(1).strip()
                    index_num = int(index_match.group(2))
                    
                    # Look for base field in field_map
                    if base_field in field_map:
                        base_value = field_map[base_field]
                        # Try to split by comma and extract the Nth element
                        parts = [p.strip() for p in base_value.split(',')]
                        if index_num <= len(parts):
                            val_to_inject = parts[index_num - 1]  # 1-indexed
                            print(f"[DEBUG INDEXED FIELD] '{data_field}' <- split from '{base_field}' => '{val_to_inject[:50]}'")
                
                # 3. Normalized match (strip punctuation/special chars) — NO partial match
                if val_to_inject is None:
                    norm_data_field = normalize_key(data_field)
                    for key, value in field_map.items():
                        norm_key = normalize_key(key)
                        if norm_data_field == norm_key:
                            val_to_inject = value
                            break
            
            # 4. Fallback via data-hint (safer semantic bridge for mismatched data-field names)
            if val_to_inject is None:
                hint_match = re.search(
                    r'\bdata-hint\s*=\s*["\']([^"\']+)["\']',
                    full_tag,
                    re.IGNORECASE,
                )
                if hint_match:
                    hint_label = html.unescape(hint_match.group(1)).strip()
                    val_to_inject = match_value_by_label(hint_label)
                    if val_to_inject is not None:
                        print(
                            f"[DEBUG DATA-HINT MATCH] data-field='{data_field}' hint='{hint_label}' => '{val_to_inject[:50] if val_to_inject else ''}'"
                        )

            if val_to_inject is not None:
                filled_count_data_field += 1
                print(f"[DEBUG DATA-FIELD MATCH] '{data_field}' => '{val_to_inject[:50] if val_to_inject else ''}'")
                # Escape quotes in value
                safe_val = str(val_to_inject).replace('"', "&quot;")

                # Check if value attribute already exists
                if re.search(r'\bvalue\s*=\s*"[^"]*"', full_tag):
                    return re.sub(
                        r'(\bvalue\s*=\s*)"[^"]*"', f'\\1"{safe_val}"', full_tag
                    )
                elif re.search(r"\bvalue\s*=\s*'[^']*'", full_tag):
                    return re.sub(
                        r"(\bvalue\s*=\s*)'[^']*'", f"\\1'{safe_val}'", full_tag
                    )
                else:
                    return re.sub(
                        r"(?i)<input\b", f'<input value="{safe_val}"', full_tag, count=1
                    )

            else:
                print(f"[DEBUG DATA-FIELD MISS] No match for data-field='{data_field}'")

            return full_tag

        def replace_input_without_data_field(match):
            nonlocal current_value_index, filled_count_sequential
            full_tag = match.group(0)

            # Only fill if we have values left
            if current_value_index < len(field_values):
                val_to_inject = field_values[current_value_index]
                current_value_index += 1

                filled_count_sequential += 1
                # Escape quotes in value
                safe_val = str(val_to_inject).replace('"', "&quot;")

                # Check if value attribute already exists
                if re.search(r'\bvalue\s*=\s*"[^"]*"', full_tag):
                    return re.sub(
                        r'(\bvalue\s*=\s*)"[^"]*"', f'\\1"{safe_val}"', full_tag
                    )
                elif re.search(r"\bvalue\s*=\s*'[^']*'", full_tag):
                    return re.sub(
                        r"(\bvalue\s*=\s*)'[^']*'", f"\\1'{safe_val}'", full_tag
                    )
                else:
                    # Add new value attribute
                    return re.sub(
                        r"(?i)<input\b", f'<input value="{safe_val}"', full_tag, count=1
                    )
                if existing_value_match:
                    # Replace existing value regardless of content
                    replacement = r"\1\2" + safe_val + r"\2"
                    return re.sub(
                        r'(\bvalue\s*=\s*)(["\'])([^"\']*)\2',
                        replacement,
                        full_tag,
                    )
                else:
                    # Add new value attribute
                    return re.sub(
                        r"(?i)<input\b", f'<input value="{safe_val}"', full_tag, count=1
                    )

            return full_tag

        output_html = html_content

        # Step 1: Fill all inputs with data-field attributes first (exact matches)
        pattern_data_field = re.compile(
            r'<input[^>]*?data-field\s*=\s*["\']([^"\']+)["\'][^>]*>', re.IGNORECASE
        )
        output_html = pattern_data_field.sub(replace_input_with_data_field, output_html)

        # Step 2: Fill remaining inputs without data-field attributes sequentially
        # This matches inputs that DON'T have data-field
        pattern_no_data_field = re.compile(
            r"<input\b(?![^>]*?data-field)[^>]*>", re.IGNORECASE
        )
        if not strict_data_field_only:
            output_html = pattern_no_data_field.sub(
                replace_input_without_data_field, output_html
            )

        # Step 3: Fill contenteditable cells/spans/divs
        # Priority: data-field attribute > label-aware matching > sequential fallback
        soup = BeautifulSoup(output_html, "lxml")
        editable_nodes = soup.select('[contenteditable="true"]')

        for node in editable_nodes:
            val_to_inject = None

            # Priority 1: Check for data-field attribute (most precise)
            data_field_attr = node.get("data-field", "").strip()
            if data_field_attr:
                data_field_lower = html.unescape(data_field_attr).lower().strip()

                # 1a. Exact lowercased match
                if data_field_lower in field_map:
                    val_to_inject = field_map[data_field_lower]
                else:
                    # 1b. Check for indexed field (e.g., "closing time (ms) 1" -> base "closing time (ms)" + index)
                    index_match = re.search(r'(.*?)\s+(\d+)$', data_field_lower)
                    if index_match:
                        base_field = index_match.group(1).strip()
                        index_num = int(index_match.group(2))
                        
                        # Look for base field in field_map
                        if base_field in field_map:
                            base_value = field_map[base_field]
                            # Try to split by comma and extract the Nth element
                            parts = [p.strip() for p in base_value.split(',')]
                            if index_num <= len(parts):
                                val_to_inject = parts[index_num - 1]  # 1-indexed
                                print(f"[DEBUG INDEXED FIELD (contenteditable)] '{data_field_attr}' <- split from '{base_field}' => '{val_to_inject[:50]}'")
                    
                    # 1c. Normalized match only (strip punctuation/spaces)
                    # DO NOT use partial containment — it causes cross-field contamination
                    if val_to_inject is None:
                        norm_df = normalize_key(data_field_lower)
                        for key, value in field_map.items():
                            if normalize_key(key) == norm_df:
                                val_to_inject = value
                                break

                if val_to_inject is not None:
                    filled_count_data_field += 1
                    print(f"[DEBUG DATA-FIELD MATCH (contenteditable)] '{data_field_attr}' => '{val_to_inject[:50] if val_to_inject else ''}'")
                else:
                    print(f"[DEBUG DATA-FIELD MISS (contenteditable)] No match for data-field='{data_field_attr}'")
            
            # Priority 2: Label-aware matching (infer from nearby label cell)
            if val_to_inject is None and not data_field_attr:
                label_candidate = ""

                # Table case: infer from nearest non-editable cell to the left.
                row = node.find_parent("tr")
                if row:
                    row_cells = row.find_all(["td", "th"], recursive=False)
                    if node in row_cells:
                        idx = row_cells.index(node)
                        for j in range(idx - 1, -1, -1):
                            left = row_cells[j]
                            if str(left.get("contenteditable", "")).lower() == "true":
                                continue
                            txt = left.get_text(" ", strip=True)
                            if txt and txt not in {"-", ":", "OK/NOT"}:
                                label_candidate = txt
                                break

                # Inline/footer case: infer from previous sibling text.
                if not label_candidate:
                    for sibling in node.previous_siblings:
                        if hasattr(sibling, "get_text"):
                            txt = sibling.get_text(" ", strip=True)
                            if txt and txt not in {":", "-", "•"}:
                                label_candidate = txt
                                break

                if label_candidate:
                    val_to_inject = match_value_by_label(label_candidate)

            # Priority 3: Sequential fill (last resort for fields without data-field)
            if (
                not strict_data_field_only
                and val_to_inject is None
                and not data_field_attr
                and current_value_index < len(field_values)
            ):
                val_to_inject = field_values[current_value_index]
                current_value_index += 1

            if val_to_inject is not None:
                # ── Post-processing: validate qualitative fields dynamically ──
                data_hint = node.get("data-hint", "").strip()
                hint_lower = data_hint.lower()
                if hint_lower.startswith("only exact handwritten word") and val_to_inject:
                    # Parse allowed values directly from the hint itself
                    # Format: "ONLY exact handwritten word: ok/okay/good/nice/..."
                    allowed = set()
                    if ":" in data_hint:
                        values_part = data_hint.split(":", 1)[1].strip()
                        for v in values_part.split("/"):
                            v = v.strip()
                            if v:
                                allowed.add(v.lower())

                    if allowed:
                        val_lower = val_to_inject.strip().lower().rstrip(".")
                        if val_lower and val_lower not in allowed:
                            coerced = self._coerce_qualitative_value(val_to_inject, allowed)
                            if coerced:
                                print(
                                    f"[VALIDATION CORRECT] data-field='{data_field_attr}' "
                                    f"value='{val_to_inject}' -> '{coerced}'"
                                )
                                val_to_inject = coerced
                            else:
                                print(
                                    f"[VALIDATION WARN] data-field='{data_field_attr}' "
                                    f"value='{val_to_inject}' not in allowed={allowed} — kept raw"
                                )

            if val_to_inject is not None:
                node.string = str(val_to_inject)
                filled_count_contenteditable += 1

        output_html = str(soup)

        print(
            f"[DEBUG] Filled {filled_count_data_field} fields with data-field, {filled_count_sequential} input fields sequentially, {filled_count_contenteditable} contenteditable fields sequentially"
        )
        return output_html

    def generate_html_from_data(self, document_type: str, page_data: PageData) -> str:
        """
        Auto-generate a styled A4 HTML page from extracted OCR data.
        Used as a fallback when no pre-built template exists.
        """
        title = page_data.title or document_type or "Document"

        rows_html = ""
        for field in page_data.extracted_fields:
            rows_html += (
                f"        <tr>\n"
                f'          <td style="font-weight:bold;width:50%;background:#f9f9f9;">{field.key}</td>\n'
                f"          <td>{field.value}</td>\n"
                f"        </tr>\n"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ background-color:#f0f2f5; margin:0; padding:40px; display:flex; justify-content:center; font-family:'Segoe UI',Tahoma,sans-serif; }}
  .a4-page {{ width:210mm; min-height:297mm; padding:20mm; background:white; box-shadow:0 4px 6px rgba(0,0,0,0.1); box-sizing:border-box; }}
  h1 {{ text-align:center; font-size:18px; text-transform:uppercase; border-bottom:2px solid #333; padding-bottom:10px; margin-bottom:20px; }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:20px; }}
  th, td {{ border:1px solid #000; padding:8px; text-align:left; vertical-align:top; font-size:12px; }}
  th {{ background:#e8e8e8; font-weight:bold; }}
  @media print {{ body {{ background:none; padding:0; }} .a4-page {{ box-shadow:none; margin:0; width:100%; }} @page {{ size:A4; margin:10mm; }} }}
</style>
</head>
<body>
  <div class="a4-page">
    <h1>{title}</h1>
    <table>
      <thead><tr><th>Field</th><th>Value</th></tr></thead>
      <tbody>
{rows_html}
      </tbody>
    </table>
  </div>
</body>
</html>"""

    def process_document_html(
        self, document_type: str, pages: List[PageData]
    ) -> Optional[Union[str, List[str]]]:
        """
        Complete workflow: load template and fill with data from all pages.
        Falls back to auto-generating HTML if no template exists.
        """
        if document_type == "TEST CERTIFICATE OF NUMERICAL RELAY RMU":
            html_content1 = self.load_template("rmu_test_report_page_1.html")
            html_content2 = self.load_template("double page/rmu_test_report_page_2.html")
            
            if html_content1 and html_content2:
                # Page 2 uniquely has 'Breaking Capacity', 'Type of Breaker', 'Earth bus', 'Closing Coil', etc.
                def is_page_2(page):
                    page2_keywords = ["breaking capacity", "type of breaker", "earth bus", "closing coil", "tripping coil"]
                    for field in page.extracted_fields:
                        if any(kw in str(field.key).lower() for kw in page2_keywords):
                            return True
                    return False
                
                page1_pdf_pages = [p for p in pages if not is_page_2(p)]
                page2_pdf_pages = [p for p in pages if is_page_2(p)]
                
                # Handle Case: Both pages present
                if page1_pdf_pages and page2_pdf_pages:
                    # Fill Page 1 using ALL pages (data-field matching handles exact placement)
                    filled_page_1 = self.fill_template_with_data(html_content1, pages, document_type)
                    
                    # Fill Page 2 using ALL page 2 data (no need to skip fields anymore,
                    # data-field attributes ensure each value goes to the correct input)
                    filled_page_2 = self.fill_template_with_data(html_content2, page2_pdf_pages, document_type)
                    return [filled_page_1, filled_page_2]
                
                # Fallback for single page or unexpected count
                filled_page_1 = self.fill_template_with_data(html_content1, page1_pdf_pages or [pages[0]], document_type)
                filled_page_2 = self.fill_template_with_data(html_content2, page2_pdf_pages or (pages[1:] if len(pages) > 1 else []), document_type)
                return [filled_page_1, filled_page_2]

        # --- 2-page templates ---
        vcb_checklist_types = [
            "VCB MAINTENANCE CHECK LIST",
            "VCB (VACUUM CIRCUIT BREAKER) MAINTENANCE CHECK LIST",
        ]
        siemens_transformer_types = [
            "TEST CERTIFICATE OF TRANSFORMER"
        ]
        
        if document_type in vcb_checklist_types:
            html_content = self.load_template("vcb_maintenance_check_list.html")
            if html_content:
                filled_html = self.fill_template_with_data(html_content, pages, document_type)
                print(f"[DEBUG VCB] Single-page fill complete, total pages input: {len(pages)}")
                return filled_html

        if document_type in siemens_transformer_types:
            html_content1 = self.load_template("siemens/test_certificate_of_transformer.html")
            html_content2 = self.load_template("siemens/test_certificate_of_transformer_page2.html")

            if html_content1 and html_content2:
                filled_page_1 = self.fill_template_with_data(html_content1, pages, document_type)
                filled_page_2 = self.fill_template_with_data(html_content2, pages, document_type)
                print(f"[DEBUG SIEMENS TRANSFORMER] 2-page fill complete, total pages input: {len(pages)}")
                return [filled_page_1, filled_page_2]

        # ── HT Panel: single template, 2 report-page divs → split into 2 standalone pages ──
        if document_type == "HT PANEL PREVENTIVE MAINTENANCE CHECKLIST":
            ht_html_file = self.get_html_file(document_type)
            if ht_html_file:
                ht_html_content = self.load_template(ht_html_file)
                if ht_html_content:
                    filled = self.fill_template_with_data(ht_html_content, pages, document_type)
                    try:
                        from bs4 import BeautifulSoup as _BS
                        soup = _BS(filled, "html.parser")
                        page_divs = soup.find_all("div", class_="report-page")
                        if len(page_divs) >= 2:
                            head_tag = str(soup.find("head") or "")
                            html_pages = []
                            for div in page_divs:
                                standalone = (
                                    f"<!DOCTYPE html><html lang='en'>"
                                    f"{head_tag}"
                                    f"<body><div class='page-container'>{div}</div></body></html>"
                                )
                                html_pages.append(standalone)
                            print(f"[DEBUG HT PANEL] Split into {len(html_pages)} pages")
                            return html_pages
                    except Exception as split_err:
                        print(f"[DEBUG HT PANEL] Split failed ({split_err}), returning single HTML")
                    return filled  # fallback if split fails

        html_file = self.get_html_file(document_type)
        print(f"[DEBUG process_document_html] document_type='{document_type}', html_file='{html_file}'")

        if html_file:
            html_content = self.load_template(html_file)
            full_path = os.path.join(self.html_dir, html_file)
            print(f"[DEBUG process_document_html] Template path='{full_path}', exists={os.path.exists(full_path)}, loaded={'yes' if html_content else 'NO'}")
            if html_content:
                return self.fill_template_with_data(html_content, pages, document_type)
        else:
            print(f"[DEBUG process_document_html] No html_file mapping found for '{document_type}'")

        # Fallback: auto-generate HTML from the extracted data (use first page)
        print(f"[DEBUG process_document_html] FALLBACK: Using generic HTML for '{document_type}'")
        return self.generate_html_from_data(
            document_type, pages[0] if pages else PageData(page_number=1)
        )


    def extract_template_guidance(self, document_type: str) -> str:
        """
        Dynamically parse the HTML template and generate structured OCR extraction
        guidance directly from its data-field attributes and printed label text.

        Handles three table layout patterns automatically:
        1. KEY-VALUE TABLE:  Label | Value | Label | Value  (e.g. info/header tables)
        2. CHECKLIST TABLE:  Sr.No | Description(printed) | Status(field) | Remarks(field)
        3. STANDARD TABLE:   Printed headers across top, data-field cells below (e.g. CT table)

        No hardcoded field names — the HTML template is the single source of truth.
        """
        # Resolve all template files for this document type
        html_files = []

        vcb_checklist_types = [
            "VCB MAINTENANCE CHECK LIST",
            "VCB (VACUUM CIRCUIT BREAKER) MAINTENANCE CHECK LIST",
        ]
        siemens_transformer_types = ["TEST CERTIFICATE OF TRANSFORMER"]

        if document_type in vcb_checklist_types:
            html_files = ["vcb_maintenance_check_list.html"]
        elif document_type in siemens_transformer_types:
            html_files = [
                "siemens/test_certificate_of_transformer.html",
                "siemens/test_certificate_of_transformer_page2.html",
            ]
        elif document_type == "TEST CERTIFICATE OF NUMERICAL RELAY RMU":
            html_files = [
                "rmu_test_report_page_1.html",
                "double page/rmu_test_report_page_2.html",
            ]
        else:
            html_file = DOCUMENT_HTML_MAPPING.get(document_type)
            if html_file:
                html_files = [html_file]

        if not html_files:
            return ""

        all_tables_guidance = []
        table_counter = 0

        for html_file in html_files:
            filepath = os.path.join(self.html_dir, html_file)
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "lxml")

            # Only process top-level tables (not nested sub-tables inside cells)
            # We detect nesting by checking if the table is inside a td/th
            all_soup_tables = soup.find_all("table")
            top_level_tables = [
                t for t in all_soup_tables
                if not t.find_parent("td") and not t.find_parent("th")
            ]

            for table in top_level_tables:
                # Collect all data-field nodes in this table (including nested sub-tables)
                data_field_nodes = table.select('[contenteditable="true"][data-field]')
                data_field_nodes += table.select('input[data-field]')

                if not data_field_nodes:
                    continue  # skip tables with no fillable fields

                table_counter += 1

                # Detect section title from preceding sibling element
                section_title = ""
                prev = table.find_previous_sibling()
                while prev:
                    txt = prev.get_text(" ", strip=True)
                    if txt and len(txt) < 150:
                        section_title = txt
                        break
                    prev = prev.find_previous_sibling()

                # ── Detect table layout pattern ──────────────────────────────────
                rows = table.find_all("tr", recursive=False)
                if not rows:
                    # Try one level deeper (thead/tbody)
                    rows = table.find_all("tr")

                # Sample up to 3 body rows (skip pure-header rows) to detect pattern
                sample_rows = [r for r in rows if r.find(attrs={"data-field": True})][:3]

                layout = self._detect_table_layout(table, sample_rows)

                # ── Generate guidance based on detected layout ───────────────────
                if layout == "key_value":
                    guidance_block = self._guidance_key_value(table, table_counter, section_title)
                elif layout == "checklist":
                    guidance_block = self._guidance_checklist(table, table_counter, section_title)
                else:  # "standard"
                    guidance_block = self._guidance_standard(table, table_counter, section_title)

                if guidance_block:
                    all_tables_guidance.append(guidance_block)

        if not all_tables_guidance:
            return ""

        guidance = "\nDYNAMIC TEMPLATE EXTRACTION RULES (auto-generated from template):\n"
        guidance += "Map EACH extracted value to its EXACT key as listed below.\n"
        guidance += "Do NOT skip columns. Do NOT merge adjacent values.\n\n"
        guidance += "\n\n".join(all_tables_guidance)
        guidance += "\n"
        return guidance

    # ── Layout detection ────────────────────────────────────────────────────────

    def _detect_table_layout(self, table, sample_rows: list) -> str:
        """
        Detect table layout pattern by examining a few representative rows.

        KEY-VALUE:  Label(short) | Value(field) | Label(short) | Value(field)
                    e.g. CLINT | [name] | VOLTEGE | [number]
        CHECKLIST:  Sr.No | Description(LONG text) | Status(field) | Remarks(field)
        STANDARD:   Printed header row on top, data rows below (CT table, etc.)

        Returns: "key_value" | "checklist" | "standard"
        """
        if not sample_rows:
            return "standard"

        # Checklist detection takes priority: any row has a LONG printed description (>20 chars)
        for row in sample_rows:
            cells = row.find_all(["td", "th"], recursive=False)
            long_labels = [
                c for c in cells
                if not c.get("data-field")
                and not c.get("contenteditable")
                and len(c.get_text(strip=True)) > 20
            ]
            if long_labels:
                return "checklist"

        # Key-value: ALL label cells are SHORT (≤20 chars), rows have both labels and fields
        kv_evidence = 0
        for row in sample_rows:
            cells = row.find_all(["td", "th"], recursive=False)
            fields = [c for c in cells if c.get("data-field")]
            # Short labels only — "CLINT", "VOLTEGE", "PANAL NO." etc.
            short_labels = [
                c for c in cells
                if not c.get("data-field")
                and not c.get("contenteditable")
                and 0 < len(c.get_text(strip=True)) <= 20
            ]
            if fields and short_labels and len(cells) <= 6:
                kv_evidence += 1

        if kv_evidence >= len(sample_rows) and len(sample_rows) > 0:
            return "key_value"

        return "standard"

    # ── Key-value table guidance ────────────────────────────────────────────────

    def _guidance_key_value(self, table, counter: int, section_title: str) -> str:
        """
        Generate guidance for Label|Value|Label|Value header tables.
        Includes data-hint attributes as format clues for the OCR model.
        """
        lines = [f"TABLE {counter} — KEY-VALUE HEADER TABLE"]
        if section_title:
            lines[0] += f" ({section_title})"
        lines.append("  LAYOUT: Each row = [Printed Label | Handwritten Value | Printed Label | Handwritten Value]")
        lines.append("  RULE: Read BOTH left AND right pairs on EVERY row before moving to the next row.")
        lines.append("  RULE: Do NOT shift values between rows. The printed label IS the row anchor.")
        lines.append("  CRITICAL: Large handwriting may visually overflow into the row below.")
        lines.append("    → Always assign the value to the row where the PRINTED LABEL appears.")
        lines.append("    → Look for the value immediately to the right of its label cell.\n")

        rows = table.find_all("tr")
        row_num = 0
        for row in rows:
            cells = row.find_all(["td", "th"], recursive=False)
            has_fields = any(c.get("data-field") for c in cells)
            if not has_fields:
                continue

            row_num += 1
            pairs = []
            i = 0
            while i < len(cells):
                cell = cells[i]
                df = cell.get("data-field", "").strip()
                if df:
                    # Value cell — read label from previous cell, hint from this cell
                    label = cells[i - 1].get_text(" ", strip=True) if i > 0 else "?"
                    hint = cell.get("data-hint", "").strip()
                    pair = f'"{label}" → key="{df}"'
                    if hint:
                        pair += f" [{hint}]"
                    pairs.append(pair)
                i += 1

            if pairs:
                prefix = "  Row 1 (top)" if row_num == 1 else f"  Row {row_num}"
                lines.append(f"{prefix}: {' | '.join(pairs)}")

        return "\n".join(lines)

    # ── Checklist table guidance ────────────────────────────────────────────────

    def _guidance_checklist(self, table, counter: int, section_title: str) -> str:
        """
        Generate guidance for checklist tables where each row has a printed
        description and one or more data-field cells (e.g. Status, Remarks).

        Dynamically classifies columns as qualitative (Status/Remarks → text)
        vs numeric so the OCR never fills text-only cells with measurement numbers.
        """
        lines = [f"TABLE {counter} — CHECKLIST TABLE"]
        if section_title:
            lines[0] += f" ({section_title})"

        # ── Detect column headers ────────────────────────────────────────────
        header_labels = []
        thead = table.find("thead")
        if thead:
            hrow = thead.find("tr")
            if hrow:
                header_labels = [c.get_text(" ", strip=True) for c in hrow.find_all(["th", "td"])]

        # Classify each header as qualitative or numeric (based on header text)
        QUALITATIVE_HEADERS = {"status", "remarks", "remark", "observation", "condition", "result", "comment"}
        NUMERIC_HEADERS = {"resistance", "current", "voltage", "reading", "value", "mw", "mva", "kv"}

        col_type = {}  # header_label → "qualitative" | "numeric" | "unknown"
        for h in header_labels:
            hl = h.lower().strip()
            if any(q in hl for q in QUALITATIVE_HEADERS):
                col_type[h] = "qualitative"
            elif any(n in hl for n in NUMERIC_HEADERS):
                col_type[h] = "numeric"
            else:
                col_type[h] = "unknown"

        # Build column type summary for the prompt
        has_qualitative = any(v == "qualitative" for v in col_type.values())

        lines.append("  LAYOUT: Each row = [Sr.No. | Printed Description | Editable field(s)]")
        lines.append("  RULE: Extract values STRICTLY per-column. Do NOT merge cells.\n")

        if header_labels:
            lines.append(f"  Column headers: {' | '.join(h for h in header_labels if h)}")

        # ── CRITICAL type constraint based on column classification ──────────
        if has_qualitative:
            qualitative_cols = [h for h, t in col_type.items() if t == "qualitative"]
            lines.append(
                f"\n  CRITICAL — {' and '.join(qualitative_cols)} columns ONLY contain SHORT qualitative "
                f"observation words. The ONLY acceptable values are:"
            )
            lines.append(
                "    ALLOWED: ok, okay, OK, nice, Nice, good, Good, great, Great, perfect, Perfect, "
                "done, Done, better, fine, Fine, checked, Checked, N/A, NA, Yes, No, -, "
                "satisfactory, Satisfactory, normal, Normal, healthy, Healthy"
            )
            lines.append(
                "  STRICT RULES for these columns:"
            )
            lines.append(
                "    1. Transcribe ONLY the EXACT handwritten word — do NOT paraphrase, translate, or invent."
            )
            lines.append(
                "    2. If a cell is empty or you cannot read it clearly, return EMPTY STRING — never guess."
            )
            lines.append(
                "    3. NEVER put a numeric measurement (resistance Ω, current A, voltage V) here."
            )
            lines.append(
                "    4. NEVER use words like 'extrac', 'alloate', 'wonderful', 'excellent', 'allocate' "
                "or any unusual/invented word. Only short status words from the ALLOWED list above."
            )
            lines.append(
                "  Numeric measurements for resistance/current ONLY belong in the IR or CT tables below.\n"
            )

        # ── Per-row field mapping ────────────────────────────────────────────
        tbody = table.find("tbody") or table
        data_rows = (
            tbody.find_all("tr", recursive=False)
            if tbody.name != "table"
            else tbody.find_all("tr")
        )

        for row in data_rows:
            cells = row.find_all(["td", "th"], recursive=False)
            field_cells = [(c.get("data-field", "").strip(), c) for c in cells if c.get("data-field")]
            if not field_cells:
                continue

            # Row description = longest non-field text cell
            desc = ""
            for c in cells:
                if not c.get("data-field") and not c.get("contenteditable"):
                    txt = c.get_text(" ", strip=True)
                    if len(txt) > len(desc):
                        desc = txt

            # Build field list with type hint where known
            field_parts = []
            for i, (df, cell) in enumerate(field_cells):
                # Match to the corresponding header column (by position)
                # Header col positions: [Sr.No | Description | field1 | field2 ...]
                # data-field columns start after the non-field cells
                non_field_count = sum(1 for c in cells if not c.get("data-field"))
                header_idx = non_field_count + i
                h = header_labels[header_idx] if header_idx < len(header_labels) else ""
                hint = cell.get("data-hint", "").strip()
                ctype = col_type.get(h, "unknown")

                part = f'"{df}"'
                if hint:
                    part += f" [{hint}]"
                elif ctype == "qualitative":
                    part += " [qualitative text: nice/Good/ok/okay/N/A]"
                field_parts.append(part)

            if desc:
                lines.append(f'  Row "{desc}": {" + ".join(field_parts)}')
            else:
                for part in field_parts:
                    lines.append(f"  key={part}")

        return "\n".join(lines)

    # ── Standard header-row table guidance ─────────────────────────────────────

    def _guidance_standard(self, table, counter: int, section_title: str) -> str:
        """
        Generate guidance for standard/mixed tables.
        For every data-field cell, emit:
          - The nearest printed label from the same row (cell immediately before)
          - The data-hint attribute if present
        This ensures the LLM can anchor each key to its correct visual column.
        """
        lines = [f"TABLE {counter} — DATA TABLE"]
        if section_title:
            lines[0] += f" ({section_title})"

        # Extract column headers from first row (if it has no data-field cells)
        first_row = table.find("tr")
        if first_row:
            header_cells = first_row.find_all(["th", "td"])
            has_data = any(c.get("data-field") for c in header_cells)
            if not has_data:
                headers = [c.get_text(" ", strip=True) for c in header_cells if c.get_text(strip=True)]
                if headers:
                    lines.append(f"  Column Headers: {' | '.join(headers)}")

        lines.append("  RULE: Map each value to its EXACT key. Use the printed label as anchor.")
        lines.append("  RULE: Do NOT merge adjacent columns. Do NOT shift values between rows.\n")

        rows = table.find_all("tr")
        row_count = 0
        for row in rows:
            cells = row.find_all(["td", "th"], recursive=False)
            data_cells = [c for c in cells if c.get("data-field")]
            if not data_cells:
                continue

            row_count += 1

            # Row anchor: first short non-field cell text (e.g. "LT row", "ST row")
            row_label = ""
            for c in cells:
                if not c.get("data-field") and not c.get("contenteditable"):
                    txt = c.get_text(" ", strip=True)
                    if txt and len(txt) < 30 and txt != ":":
                        row_label = txt
                        break

            row_prefix = f"  Row {row_label!r}" if row_label else f"  Row {row_count}"
            pairs = []

            for i, cell in enumerate(cells):
                df = cell.get("data-field", "").strip()
                if not df:
                    continue

                hint = cell.get("data-hint", "").strip()

                # Find the nearest preceding label in this row (skip ":" separators)
                label = ""
                for prev_cell in reversed(cells[:i]):
                    if prev_cell.get("data-field") or prev_cell.get("contenteditable"):
                        continue
                    txt = prev_cell.get_text(" ", strip=True)
                    if txt and txt != ":" and len(txt) < 30:
                        label = txt
                        break

                entry = f'"{label}" → key="{df}"' if label else f'key="{df}"'
                if hint:
                    entry += f" [{hint}]"
                pairs.append(entry)

            if pairs:
                lines.append(f"{row_prefix}: {' | '.join(pairs)}")

        return "\n".join(lines)


    def get_all_template_data_fields(self, document_type: str) -> list:
        """
        Return a flat list of all data-field attribute values from the template(s)
        for a given document type. Useful for building the OCR key list dynamically.
        """
        html_files = []
        
        vcb_checklist_types = [
            "VCB MAINTENANCE CHECK LIST",
            "VCB (VACUUM CIRCUIT BREAKER) MAINTENANCE CHECK LIST",
        ]
        siemens_transformer_types = ["TEST CERTIFICATE OF TRANSFORMER"]
        
        if document_type in vcb_checklist_types:
            html_files = ["vcb_maintenance_check_list.html"]
        elif document_type in siemens_transformer_types:
            html_files = [
                "siemens/test_certificate_of_transformer.html",
                "siemens/test_certificate_of_transformer_page2.html",
            ]
        elif document_type == "TEST CERTIFICATE OF NUMERICAL RELAY RMU":
            html_files = [
                "Reports Htmls/rmu_test_report_page_1.html",
                "Reports Htmls/rmu_test_report_page_2.html",
            ]
        else:
            html_file = DOCUMENT_HTML_MAPPING.get(document_type)
            if html_file:
                html_files = [html_file]

        all_fields = []
        for html_file in html_files:
            filepath = os.path.join(self.html_dir, html_file)
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "lxml")

            # Contenteditable elements with data-field
            for node in soup.select('[contenteditable="true"][data-field]'):
                df = node.get("data-field", "").strip()
                if df and df not in all_fields:
                    all_fields.append(df)

            # Input elements with data-field
            for node in soup.select('input[data-field]'):
                df = node.get("data-field", "").strip()
                if df and df not in all_fields:
                    all_fields.append(df)

        return all_fields


# Global instance
html_template_service = HTMLTemplateService()
