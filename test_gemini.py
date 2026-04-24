"""
Simple test to verify Gemini API is working
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Get API key
API_KEY = os.getenv('GEMINI_API_KEY')

if not API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)

# Configure Gemini
genai.configure(api_key=API_KEY)

# List available models
print("📋 Available Gemini Models:")
print("=" * 60)
try:
    models = genai.list_models()
    available_models = []
    for model in models:
        if "generateContent" in model.supported_generation_methods:
            available_models.append(model.name)
            print(f"✅ {model.name}")
    print("=" * 60)
    print(f"\nTotal models available: {len(available_models)}\n")
except Exception as e:
    print(f"❌ Error listing models: {str(e)}\n")

# Create model - use an available model
print("🔄 Testing Gemini API...")
print("Sending prompt: 'Say hello world'")

available_model = "gemini-2.5-flash"  # Use the available model
try:
    model = genai.GenerativeModel(available_model)
    response = model.generate_content("Say hello world")
    print(f"\n✅ SUCCESS! Gemini responded:")
    print(f"\n{response.text}")
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

