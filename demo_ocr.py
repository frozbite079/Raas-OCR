import os
import io
import base64
from PIL import Image, ImageEnhance
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Load environment variables (ensure OPENAI_API_KEY is set)
load_dotenv()

def extract_text_from_image(image_path: str, contrast_factor=1.5):
    """
    Demonstrates how to perform OCR using gpt-4o-mini with vision,
    mirroring the exact configuration used in the Raas-OCR application.
    
    Args:
        image_path: Path to image file
        contrast_factor: Contrast enhancement factor (1.0 = original, >1.0 = increased contrast)
    """
    print(f"Loading image from: {image_path}")
    
    try:
        # Load image directly using PIL
        image = Image.open(image_path)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # --- Image Preprocessing: Enhance Contrast ---
        print(f"Enhancing image contrast (factor: {contrast_factor})...")
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(contrast_factor)
            
        # Convert image to base64 format required by OpenAI
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
    except Exception as e:
        print(f"Failed to load image: {e}")
        return

    # Initialize the LLM (same settings as ocr_service.py)
    print("Initializing gpt-4o-mini model...")
    #llm = ChatOpenAI(model="GLM-4.6V-Flash", temperature=0, max_tokens=16384,base_url="https://api.z.ai/api/paas/v4/",api_key="acf9490ad2234746b071fb492d2eb49a.9lYnlrjORzzPdefc")
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0, max_tokens=16384)
    #llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=16384,base_url="https://api.aicredits.in/v1")
    """
    Detail need is - "Def. Time Over current protection	",High set over current,Time delay	of both "DEFINITE TIME O/C" and 	DEFINITE TIME EF	
just give full detail with all feilds of all section in json format only. - dont miss any feild 
- 
.
    """
    # Define the OCR extraction prompt
    prompt = """
    You are an expert OCR and data extraction system.
    {

  "header_details": {
    "client": "",
    "plant": "",
    "swbd": "",
    "feeder": "",
    "tested_on": "",
    "tested_by": ""
  },

  "sections": {
    "1_0_current_transformer_test": {

      "1_1_metering_core": {

        "table_columns": [
          "phase",
          "sr_no",
          "ratio",
          "va",
          "accuracy_class",
          "polarity",
          "ct_resistance_ohm",
          "primary_injected_current_a",
          "secondary_current",
          "meter_reading_amp"
        ],

        "rows": [
          {
            "phase": "",
            "sr_no": "",
            "ratio": "",
            "va": "",
            "accuracy_class": "",
            "polarity": "",
            "ct_resistance_ohm": "",
            "primary_injected_current_a": "",
            "secondary_current": "",
            "meter_reading_amp": ""
          }
        ]
      },

      "1_2_protection_core": {

        "table_columns": [
          "phase",
          "sr_no",
          "ratio",
          "va",
          "accuracy_class",
          "polarity",
          "ct_resistance_ohm",
          "primary_injected_current_a",
          "secondary_current",
          "meter_reading_amp"
        ],

        "rows": [
          {
            "phase": "",
            "sr_no": "",
            "ratio": "",
            "va": "",
            "accuracy_class": "",
            "polarity": "",
            "ct_resistance_ohm": "",
            "primary_injected_current_a": "",
            "secondary_current": "",
            "meter_reading_amp": ""
          }
        ]
      }
    }
  },

  "remarks": "",

  "raw_metadata": {
    "document_type": "",
    "total_tables": "",
    "language": ""
  }
}


}
Critical:
you are putting wrong 'va' values in 'ratio' fields , make it correct, align ment should be good
Dont hallucinate. give a proper answer. with confidence score
"""

    # Build the message payload with high-detail vision mode
    print("Sending request to OpenAI API (detail: 'high')...")
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_base64}",
                    "detail": "high"  # High detail ensures accuracy on dense tables
                },
            },
        ]
    )

    try:
        # Invoke the LLM
        response = llm.invoke([message])
        
        # Print token usage
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            print(f"\n--- TOKEN USAGE ---")
            print(f"Prompt Tokens: {usage.get('input_tokens')}")
            print(f"Completion Tokens: {usage.get('output_tokens')}")
            print(f"Total Tokens: {usage.get('total_tokens')}")
            print(f"-------------------\n")
        elif 'token_usage' in response.response_metadata:
            usage = response.response_metadata['token_usage']
            print(f"\n--- TOKEN USAGE ---")
            print(f"Prompt Tokens: {usage.get('prompt_tokens')}")
            print(f"Completion Tokens: {usage.get('completion_tokens')}")
            print(f"Total Tokens: {usage.get('total_tokens')}")
            print(f"-------------------\n")
            
        # Print the results
        print("\n=== EXTRACTION RESULTS ===")
        print(response.content)
        print("==========================")
        
        # Save to file for reliable reading
        with open("extraction_result.json", "w") as f:
            f.write(response.content)
        print("\nResults saved to extraction_result.json")
        
    except Exception as e:
        print(f"Error during API call: {e}")

if __name__ == "__main__":
    # Example usage: Replace with an actual image path
    # E.g., a test image from your project
    sample_image_path = "test_data/TCHSP.jpeg" 
    
    # Contrast enhancement factor (1.0 = original, 1.5 = 50% more contrast, 2.0 = 100% more)
    # Recommended: 1.3 - 2.0 for better text extraction
    contrast_factor = 1.5
    
    if os.path.exists(sample_image_path):
        extract_text_from_image(sample_image_path, contrast_factor=contrast_factor)
    else:
        print(f"Please provide a valid image path. '{sample_image_path}' not found.")
        print("Update the 'sample_image_path' variable at the bottom of the script to test.")
