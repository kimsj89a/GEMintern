import sys
import os
import json

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import utils_ppt

def test_json_ppt():
    json_data = {
        "slides": [
            {
                "type": "title",
                "title": "Test Presentation",
                "subtitle": "Generated via JSON"
            },
            {
                "type": "section",
                "title": "Section 1: Overview"
            },
            {
                "type": "content",
                "title": "Market Analysis",
                "layout": "2_column",
                "left": {
                    "title": "Key Trends",
                    "items": ["Trend 1: AI Adoption", "Trend 2: Cloud Growth"]
                },
                "right": {
                    "title": "Data Points",
                    "items": ["CAGR 20%", "Market Size $50B"]
                },
                "summary": "Market is growing fast."
            }
        ]
    }
    
    json_str = json.dumps(json_data)
    
    print("Generating PPT from JSON...")
    ppt_bytes = utils_ppt.create_deck_from_json(json_str)
    
    if ppt_bytes:
        output_path = "test_output.pptx"
        with open(output_path, "wb") as f:
            f.write(ppt_bytes)
        print(f"Success! Saved to {output_path}")
    else:
        print("Failed to generate PPT.")

if __name__ == "__main__":
    test_json_ppt()
