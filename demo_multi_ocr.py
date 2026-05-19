"""
demo_multi_ocr.py
-----------------
Multi-Part OCR Demo for RMU documents.
Makes separate, focused API calls for each section and merges all results.
This proves the technique before we integrate it into ocr_service.py.

Usage:
    python demo_multi_ocr.py page1_rmu.jpeg
"""

import os
import io
import json
import base64
import asyncio
import sys
from PIL import Image
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

# ─── IMAGE LOADER ────────────────────────────────────────────────────────────

def load_image_as_base64(image_path: str) -> str:
    image = Image.open(image_path)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()


# ─── SINGLE CALL HELPER ──────────────────────────────────────────────────────

def call_llm(llm: ChatOpenAI, img_b64: str, prompt: str, part_name: str) -> list:
    """Make one focused API call and return a list of {key, value} dicts."""
    print(f"\n  📤 Sending Part: [{part_name}]...")
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_b64}",
                    "detail": "high",
                },
            },
        ]
    )
    response = llm.invoke([message])
    raw = response.content.strip()

    # Strip markdown code fences if present
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    try:
        data = json.loads(raw.strip())
        fields = data.get("fields", [])
        print(f"  ✅ [{part_name}] returned {len(fields)} fields")
        return fields
    except json.JSONDecodeError as e:
        print(f"  ❌ [{part_name}] JSON parse error: {e}")
        print(f"  Raw response: {raw[:300]}")
        return []


# ─── PART PROMPTS ────────────────────────────────────────────────────────────

PART_1_HEADER = """
Look at the HEADER TABLE at the top of this RMU Test Certificate document.
The header has these labeled cells:
  - "Client"    → the handwritten client name
  - "Tested On" → the date (right side, top row)
  - "Plant"     → the handwritten plant name
  - "Tested By" → the person's name (right side, middle row)
  - "Feeder"    → the handwritten feeder name (bottom row)

Read each cell strictly by its printed label. Do NOT mix up "Tested On" and "Tested By".

Return ONLY this JSON:
{
  "fields": [
    {"key": "Client",     "value": "<handwritten value>"},
    {"key": "Tested On",  "value": "<handwritten value>"},
    {"key": "Plant",      "value": "<handwritten value>"},
    {"key": "Tested By",  "value": "<handwritten value>"},
    {"key": "Feeder",     "value": "<handwritten value>"}
  ]
}
"""

PART_2_NAMEPLATE = """
Look ONLY at Section 1.0 "Name Plate Details of Relay" table.
This table has exactly 5 columns in left-to-right order:
  Column 1: Make
  Column 2: Relay Model No.
  Column 3: Relay Serial No.
  Column 4: IN (Amp)
  Column 5: Aux. Supply

There is ONE row of handwritten values below the column headers.
Read each column cell INDEPENDENTLY. Do NOT merge adjacent cells.

Return ONLY this JSON:
{
  "fields": [
    {"key": "Relay Make",        "value": "<column 1 value only>"},
    {"key": "Relay Model No.",   "value": "<column 2 value only>"},
    {"key": "Relay Serial No.",  "value": "<column 3 value only>"},
    {"key": "IN (Amp)",          "value": "<column 4 value only>"},
    {"key": "Aux. Supply",       "value": "<column 5 value only>"}
  ]
}
"""

PART_3_SETTINGS = """
Look ONLY at Section 2.0 "Relay Range & Settings" table.
This section has TWO sub-groups: "DEFINITE TIME O/C" and "DEFINITE TIME EF".
Each sub-group has rows:
  - "Def. Time Over current protection" (or "Def. Time Earth Fault Protection")
  - "High set over current"
  - "Time delay"

For each row extract the SETTING value from the rightmost column.
Do NOT extract values from the "Protection" column (middle).
Prefix keys with the group name, e.g. "O/C Def. Time Over current protection".

Return ONLY this JSON:
{
  "fields": [
    {"key": "O/C Def. Time Over current protection", "value": "<setting value>"},
    {"key": "O/C High set over current",              "value": "<setting value>"},
    {"key": "O/C Time delay",                         "value": "<setting value>"},
    {"key": "EF Def. Time Earth Fault Protection",   "value": "<setting value>"},
    {"key": "EF High set over current",               "value": "<setting value>"},
    {"key": "EF Time delay",                          "value": "<setting value>"}
  ]
}
"""

PART_4_OVERCURRENT = """
Look ONLY at Section 4.0 "Testing of over current unit" table.
This table has TWO halves:
  LEFT HALF  = "High set unit"    → columns: I set | I p/u | T set | Tmeas
  RIGHT HALF = "Definite time unit" → columns: I set | I p/u | T set | Tmeas

There are 3 rows: R, Y, B. Each row has 8 values total (4 left + 4 right).

Return ONLY this JSON (fill all 24 values):
{
  "fields": [
    {"key": "Over Current R I set High",      "value": ""},
    {"key": "Over Current R I p/u High",      "value": ""},
    {"key": "Over Current R T set High",      "value": ""},
    {"key": "Over Current R Tmeas High",      "value": ""},
    {"key": "Over Current R I set Definite",  "value": ""},
    {"key": "Over Current R I p/u Definite",  "value": ""},
    {"key": "Over Current R T set Definite",  "value": ""},
    {"key": "Over Current R Tmeas Definite",  "value": ""},
    {"key": "Over Current Y I set High",      "value": ""},
    {"key": "Over Current Y I p/u High",      "value": ""},
    {"key": "Over Current Y T set High",      "value": ""},
    {"key": "Over Current Y Tmeas High",      "value": ""},
    {"key": "Over Current Y I set Definite",  "value": ""},
    {"key": "Over Current Y I p/u Definite",  "value": ""},
    {"key": "Over Current Y T set Definite",  "value": ""},
    {"key": "Over Current Y Tmeas Definite",  "value": ""},
    {"key": "Over Current B I set High",      "value": ""},
    {"key": "Over Current B I p/u High",      "value": ""},
    {"key": "Over Current B T set High",      "value": ""},
    {"key": "Over Current B Tmeas High",      "value": ""},
    {"key": "Over Current B I set Definite",  "value": ""},
    {"key": "Over Current B I p/u Definite",  "value": ""},
    {"key": "Over Current B T set Definite",  "value": ""},
    {"key": "Over Current B Tmeas Definite",  "value": ""}
  ]
}
"""

PART_5_EARTHFAULT = """
Look ONLY at Section 4.1 "Testing of Earth Fault unit" table.
Same TWO-HALF structure as the Over Current table, but only 1 row: EF.
LEFT HALF  = "High set unit"    → columns: I set | I p/u | T set | Tmeas
RIGHT HALF = "Definite time unit" → columns: I set | I p/u | T set | Tmeas

Return ONLY this JSON:
{
  "fields": [
    {"key": "Earth Fault EF I set High",      "value": ""},
    {"key": "Earth Fault EF I p/u High",      "value": ""},
    {"key": "Earth Fault EF T set High",      "value": ""},
    {"key": "Earth Fault EF Tmeas High",      "value": ""},
    {"key": "Earth Fault EF I set Definite",  "value": ""},
    {"key": "Earth Fault EF I p/u Definite",  "value": ""},
    {"key": "Earth Fault EF T set Definite",  "value": ""},
    {"key": "Earth Fault EF Tmeas Definite",  "value": ""}
  ]
}
"""


# ─── MAIN MULTI-PART EXTRACTION ──────────────────────────────────────────────

def extract_rmu_multi_part(image_path: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  RMU Multi-Part OCR Demo")
    print(f"  Image: {image_path}")
    print(f"{'='*60}")

    # Load image once, reuse for all parts
    img_b64 = load_image_as_base64(image_path)

    # Init LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=4096)

    # Define all parts
    parts = [
        ("Part 1: Header",        PART_1_HEADER),
        ("Part 2: Nameplate",     PART_2_NAMEPLATE),
        ("Part 3: Settings",      PART_3_SETTINGS),
        ("Part 4: Over Current",  PART_4_OVERCURRENT),
        ("Part 5: Earth Fault",   PART_5_EARTHFAULT),
    ]

    # Call each part and collect results
    merged_fields = []
    for part_name, prompt in parts:
        fields = call_llm(llm, img_b64, prompt, part_name)
        merged_fields.extend(fields)

    # Build final merged output
    result = {
        "document": "TEST CERTIFICATE OF NUMERICAL RELAY RMU",
        "total_fields": len(merged_fields),
        "fields": merged_fields,
    }

    return result


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else "page1_rmu.jpeg"

    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)

    result = extract_rmu_multi_part(image_path)

    print(f"\n{'='*60}")
    print(f"  MERGED RESULT ({result['total_fields']} fields)")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2))
