import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def call_llm(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = _client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower()
            is_unavailable = "503" in error_str or "unavailable" in error_str.lower() or "overloaded" in error_str.lower()
            
            if is_rate_limit or is_unavailable:
                if attempt < retries:
                    wait = 10 if is_unavailable else (60 if attempt == 0 else 120)
                    print(f"[LLM] Temporary error/Rate limit ({e}), waiting {wait}s before retry {attempt + 1}/{retries}...")
                    time.sleep(wait)
            else:
                print(f"[LLM] Call failed: {e}")
                raise
    print("[LLM] All retries exhausted, returning fallback.")
    return ""