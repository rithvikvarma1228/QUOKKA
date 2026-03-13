import os
import numpy as np
import faiss
import requests

from sentence_transformers import SentenceTransformer

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn


# ----------------------------
# LOAD EMBEDDING MODEL
# ----------------------------
print("Loading embedding model...")

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

print("Embedding model loaded!")


# ----------------------------
# LOAD VECTOR DATABASE
# ----------------------------
print("Loading knowledge base...")

index = faiss.read_index("index.faiss")
chunks = np.load("chunks.npy", allow_pickle=True)
sources_data = np.load("sources.npy", allow_pickle=True)

print("Knowledge base loaded!")


# ----------------------------
# MISTRAL (OLLAMA)
# ----------------------------
def ask_mistral(prompt):

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]


# ----------------------------
# RETRIEVAL FUNCTION
# ----------------------------
def retrieve_context(query, k=12):

    queries = [
        query,
        query + " crystal defect",
        query + " Frenkel defect Schottky defect definition"
    ]

    all_indices = []

    for q in queries:

        q_vec = embed_model.encode([q], normalize_embeddings=True)
        q_vec = np.array(q_vec).astype("float32")

        distances, indices = index.search(q_vec, k)

        all_indices.extend(indices[0])

    unique_indices = list(set(all_indices))

    context = ""
    sources = []

    for idx in unique_indices:

        chunk = chunks[idx]

        if len(chunk) < 120:
            continue

        if len(context) + len(chunk) > 2000:
            break

        context += chunk + "\n"
        sources.append(sources_data[idx])

    return context, sources


# ----------------------------
# CHATBOT LOGIC
# ----------------------------
def chatbot_response(query):

    context, sources = retrieve_context(query)

    print("\n============================")
    print("USER QUESTION:", query)
    print("\nRETRIEVED CONTEXT:\n")
    print(context[:1500])
    print("\n============================\n")

    if len(context.strip()) < 50:
        return "⚠️ No reliable context found. Try another question."

    prompt = f"""
You are QUOKKA, an expert materials science assistant.

Use ONLY the information from the context.

Rules:
- Summarize clearly.
- Maximum 5 sentences.
- Use bullet points when comparing concepts.
- Ignore corrupted text.
Answer ONLY using the context.
If the answer is not present in the context, say:
"The document does not contain enough information."
Do not use outside knowledge.

Context:
{context}

Question: {query}

Answer:
"""

    answer = ask_mistral(prompt)

    answer += "\n\nSources:\n- " + "\n- ".join(set(sources))

    return answer


# ----------------------------
# FASTAPI SERVER
# ----------------------------
app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend"), name="static")


class ChatRequest(BaseModel):
    message: str


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join("frontend", "index.html"))


@app.post("/api/chat")
async def api_chat(request: ChatRequest):

    full_response = chatbot_response(request.message)

    if "Sources:" in full_response:

        main_answer, sources_text = full_response.split("Sources:", 1)

        sources_list = [
            s.strip().replace("-", "").strip()
            for s in sources_text.split("\n")
            if s.strip()
        ]

    else:
        main_answer = full_response
        sources_list = []

    return {
        "answer": main_answer.strip(),
        "sources": sources_list
    }


# ----------------------------
# LAUNCH SERVER
# ----------------------------
if __name__ == "__main__":
    print("Starting FastAPI server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)