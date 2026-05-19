"""
debug_ct_page2.py
-----------------
Debug script to test extraction of Section 4.1 Protection Core (CT Test)
from page 2 of the RMU document.

Usage:
    python debug_ct_page2.py
"""

import os
import io
import json
import base64
from PIL import Image
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

IMAGE_PATH = "page2_rmu.jpeg"

# CT Protection Core keys from schemas.py
CT_KEYS = [
    "CT R Sr. No.", "CT R Ratio", "CT R VA", "CT R Acc. Class",
    "CT R Polarity", "CT R Primary Injected Current", "CT R Secondary Current", "CT R CT Resis.",
    "CT Y Sr. No.", "CT Y Ratio", "CT Y VA", "CT Y Acc. Class",
    "CT Y Polarity", "CT Y Primary Injected Current", "CT Y Secondary Current", "CT Y CT Resis.",
    "CT B Sr. No.", "CT B Ratio", "CT B VA", "CT B Acc. Class",
    "CT B Polarity", "CT B Primary Injected Current", "CT B Secondary Current", "CT B CT Resis.",
]


def load_image_as_base64(image_path: str) -> str:
    image = Image.open(image_path)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()


def main():
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Image not found: {IMAGE_PATH}")
        return

    print(f"\n{'='*60}")
    print(f"  CT Protection Core Debug — Page 2")
    print(f"  Image: {IMAGE_PATH}")
    print(f"{'='*60}")

    img_b64 = load_image_as_base64(IMAGE_PATH)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=4096)

    prompt = """Look ONLY at Section 4.1 "Protection Core" table in this RMU Test Certificate page 2.

This table has 3 rows: R, Y, B (one for each phase).
Each row has these columns in left-to-right order:
  Sr. No. | Ratio | VA | Acc. Class | Polarity | Primary Injected Current | Secondary Current | CT Resis.

Read each cell value independently for each row.

Map the values to these EXACT key names:
  Row R: "CT R Sr. No.", "CT R Ratio", "CT R VA", "CT R Acc. Class", "CT R Polarity", "CT R Primary Injected Current", "CT R Secondary Current", "CT R CT Resis."
  Row Y: "CT Y Sr. No.", "CT Y Ratio", "CT Y VA", "CT Y Acc. Class", "CT Y Polarity", "CT Y Primary Injected Current", "CT Y Secondary Current", "CT Y CT Resis."
  Row B: "CT B Sr. No.", "CT B Ratio", "CT B VA", "CT B Acc. Class", "CT B Polarity", "CT B Primary Injected Current", "CT B Secondary Current", "CT B CT Resis."

If a cell is empty, return "" (empty string).

Return ONLY this JSON:
{
  "fields": [
    {"key": "CT R Sr. No.", "value": ""}, {"key": "CT R Ratio", "value": ""}, {"key": "CT R VA", "value": ""}, {"key": "CT R Acc. Class", "value": ""},
    {"key": "CT R Polarity", "value": ""}, {"key": "CT R Primary Injected Current", "value": ""}, {"key": "CT R Secondary Current", "value": ""}, {"key": "CT R CT Resis.", "value": ""},
    {"key": "CT Y Sr. No.", "value": ""}, {"key": "CT Y Ratio", "value": ""}, {"key": "CT Y VA", "value": ""}, {"key": "CT Y Acc. Class", "value": ""},
    {"key": "CT Y Polarity", "value": ""}, {"key": "CT Y Primary Injected Current", "value": ""}, {"key": "CT Y Secondary Current", "value": ""}, {"key": "CT Y CT Resis.", "value": ""},
    {"key": "CT B Sr. No.", "value": ""}, {"key": "CT B Ratio", "value": ""}, {"key": "CT B VA", "value": ""}, {"key": "CT B Acc. Class", "value": ""},
    {"key": "CT B Polarity", "value": ""}, {"key": "CT B Primary Injected Current", "value": ""}, {"key": "CT B Secondary Current", "value": ""}, {"key": "CT B CT Resis.", "value": ""}
  ]
}"""

    print(f"\n  📤 Sending CT Protection Core extraction request...")

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

    # Strip markdown code fences
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    try:
        data = json.loads(raw.strip())
        fields = data.get("fields", [])
        print(f"  ✅ Extracted {len(fields)} CT fields\n")

        print(f"{'='*60}")
        print(f"  CT EXTRACTION RESULTS")
        print(f"{'='*60}")

        # Print nicely grouped by phase
        for phase in ["R", "Y", "B"]:
            print(f"\n  --- Phase {phase} ---")
            for f in fields:
                if f["key"].startswith(f"CT {phase}"):
                    val = f["value"] or "(empty)"
                    print(f"    {f['key']:40s} = {val}")

        print(f"\n{'='*60}")
        print(f"  FULL JSON:")
        print(f"{'='*60}")
        print(json.dumps(data, indent=2))

    except json.JSONDecodeError as e:
        print(f"  ❌ JSON parse error: {e}")
        print(f"  Raw response: {raw[:500]}")


if __name__ == "__main__":
    main()
