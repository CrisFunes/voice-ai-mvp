import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

key = os.getenv('ANTHROPIC_API_KEY')
print(f"API Key (first 30 chars): {key[:30] if key else 'NOT FOUND'}")
print(f"API Key length: {len(key) if key else 0}")
print(f"Starts with sk-ant-: {key.startswith('sk-ant-') if key else False}")

# Try basic API call
try:
    client = Anthropic(api_key=key)
    response = client.messages.create(
        model="claude-3-opus-20240229",  # Most basic model
        max_tokens=10,
        messages=[{"role": "user", "content": "Hi"}]
    )
    print("✅ API KEY WORKS!")
    print(f"Response: {response.content[0].text}")
except Exception as e:
    print(f"❌ API KEY FAILED: {str(e)}")

