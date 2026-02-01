import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set")

client = genai.Client(api_key=api_key)

for m in client.models.list():
    # show only models that support generateContent-like usage
    print(m.name)
