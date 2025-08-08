from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import os
import time
import json
import re

load_dotenv()

app = Flask(__name__)
CORS(app)

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

last_request_time = 0
REQUEST_INTERVAL = 2

def extract_json_from_text(text):
    """Extracts JSON from Gemini's response text"""
    try:
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except json.JSONDecodeError:
        return None

def get_waste_disposal_info(waste_description):
    global last_request_time
    
    current_time = time.time()
    if current_time - last_request_time < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - (current_time - last_request_time))
    last_request_time = time.time()
    
    prompt = f"""Analyze this waste description and provide response in exact JSON format:
    {{
        "classification": "category_name",
        "disposal_methods": ["method1", "method2"],
        "safety_precautions": ["precaution1", "precaution2"],
        "recycling_options": ["option1", "option2"]
    }}
    
    Waste description: {waste_description}
    
    Important:
    - Respond ONLY with valid JSON
    - Do not include any additional text or markdown
    - Escape all special characters properly"""
    
    try:
        response = model.generate_content(prompt)
        if response.text:
            json_data = extract_json_from_text(response.text)
            if json_data:
                return json_data
        return None
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        return None

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
        
        if not result:
            return jsonify({'error': 'Failed to analyze waste. Please try again.'}), 500
            
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f"System error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)