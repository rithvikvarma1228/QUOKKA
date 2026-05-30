import os
import json
import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODEL_MAP = {
    "llama3.1:8b":  "llama-3.1-8b-instant",
    "llama3.1:70b": "llama-3.3-70b-versatile",
}

DEFAULT_MODEL = "llama-3.1-8b-instant"

DEFAULT_MODEL = "llama-3.1-8b-instant"


def ask_llm_stream(prompt, model="llama3.1:8b", temperature=0.7, provider=None):
    groq_model = GROQ_MODEL_MAP.get(model, DEFAULT_MODEL)
    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY', '')}",
                "Content-Type": "application/json"
            },
            json={
                "model": groq_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": float(temperature),
                "max_tokens": 512,
                "stream": True
            },
            stream=True,
            timeout=30
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    chunk = decoded[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield f"data: {json.dumps({'text': delta})}\n\n"
                    except:
                        continue

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def ask_llm_json(prompt, model="llama3.1:8b", temperature=0.3, provider=None):
    groq_model = GROQ_MODEL_MAP.get(model, DEFAULT_MODEL)
    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY', '')}",
                "Content-Type": "application/json"
            },
            json={
                "model": groq_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": float(temperature),
                "max_tokens": 400,
                "stream": False
            },
            timeout=30
        )
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"Groq JSON error: {e}")
        return None
