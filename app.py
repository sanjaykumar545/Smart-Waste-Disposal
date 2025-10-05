from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import os
import time
import json
import re

# Load .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Use a valid Gemini model
try:
    model = genai.GenerativeModel('gemini-2.0-flash')  # You can switch to another available model if needed
    # Test connection with a simple prompt
    test_response = model.generate_content("ping")
    if test_response and hasattr(test_response, "text"):
        print("✅ Gemini API connected successfully!")
    else:
        print("⚠️ Gemini API connected but did not return text.")
except Exception as e:
    print(f"❌ Gemini API connection failed: {e}")
    model = None  # prevent crashes later

last_request_time = 0
REQUEST_INTERVAL = 2

def extract_json_from_text(text):
    """Extracts JSON from Gemini's response text"""
    try:
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except json.JSONDecodeError:
        return None

def get_waste_disposal_info(waste_description):
    global last_request_time

    if not model:
        return {"error": "Gemini API is not connected"}

    current_time = time.time()
    if current_time - last_request_time < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - (current_time - last_request_time))
    last_request_time = time.time()

    prompt = f"""You are an intelligent waste management assistant. 
The user may provide a single waste item or multiple items separated by commas/spaces.  
For **each item separately**, classify it and provide multiple safe, eco-friendly, advanced, and legal disposal methods.  

Return the result in valid JSON only, with this structure:  

{{
    "waste_items": [
        {{
            "item": "name of the waste item",
            "classification": "broad_category",
            "sub_classification": ["possible_sub_categories_if_any"],
            "disposal_methods": [
                "method1 - short explanation",
                "method2 - short explanation",
                "innovative/advanced method - short explanation"
            ],
            "safety_precautions": [
                "precaution1",
                "precaution2"
            ],
            "recycling_options": [
                "option1",
                "option2"
            ],
            "clarification_needed": "Question to ask user if item description is vague"
        }}
    ]
}}

Guidelines:
- If multiple items are given, repeat this structure for each one inside "waste_items".
- Always return all possible solutions, not just one.
- Prefer advanced and sustainable solutions.
- If an item is unclear, add a clarifying question in "clarification_needed".
- Respond ONLY with valid JSON, no extra text or markdown.

Waste description: {waste_description}"""

    try:
        response = model.generate_content(prompt)
        if response and hasattr(response, "text") and response.text:
            json_data = extract_json_from_text(response.text)
            if json_data:
                return json_data
        return {"error": "No valid response from Gemini"}
    except Exception as e:
        # Handle quota exceeded separately
        if "429" in str(e):
            return {"error": "Quota exceeded. Please wait for reset or upgrade your plan."}
        print(f"Gemini API error: {str(e)}")
        return {"error": f"Gemini API error: {str(e)}"}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze-waste', methods=['POST'])
def analyze_waste():
    try:
        data = request.json
        waste_description = data.get('waste_description', '').strip()

        if not waste_description:
            return jsonify({'error': 'Please describe your waste item'}), 400

        result = get_waste_disposal_info(waste_description)

        if "error" in result:
            # Use 429 if quota exceeded, otherwise 500
            if "Quota exceeded" in result["error"]:
                return jsonify(result), 429
            return jsonify(result), 500

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f"System error: {str(e)}"}), 500

# Health check API
@app.route('/api/health', methods=['GET'])
def health_check():
    if model:
        return jsonify({"status": "ok", "message": "Gemini API connected"}), 200
    else:
        return jsonify({"status": "error", "message": "Gemini API not connected"}), 500

if __name__ == '__main__':
    app.run(debug=True)
