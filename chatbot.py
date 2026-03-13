import numpy as np
import faiss
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM

# =====================================================
# DEVICE SETUP
# =====================================================
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

# =====================================================
# LOAD EMBEDDING MODEL
# =====================================================
print("Loading embedding model...")
embed_model = SentenceTransformer(
    "all-MiniLM-L6-v2",
    device=device
)

# =====================================================
# LOAD KNOWLEDGE BASE
# =====================================================
print("Loading knowledge base...")
index = faiss.read_index("index.faiss")
chunks = np.load("chunks.npy", allow_pickle=True)
sources = np.load("sources.npy", allow_pickle=True)
print("Knowledge base loaded!")

# =====================================================
# LOAD LLM
# =====================================================
print("Loading LLM...")
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_name)

llm_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32
).to(device)

llm_model.eval()

print("\n✅ QUOKKA is ready!\n")

# =====================================================
# CHAT LOOP
# =====================================================
while True:

    query = input("Ask a materials science question (type 'exit' to stop): ")

    if query.lower() == "exit":
        break

    # -------------------------------------------------
    # EMBED QUERY
    # -------------------------------------------------
    query_vector = embed_model.encode([query])
    query_vector = np.array(query_vector).astype("float32")

    # -------------------------------------------------
    # SEARCH VECTOR DATABASE
    # -------------------------------------------------
    distances, indices = index.search(query_vector, 8)

    context = ""
    used_sources = set()

    SIMILARITY_THRESHOLD = 1.2
    MAX_CONTEXT_CHARS = 2000

    sorted_results = sorted(
        zip(distances[0], indices[0]),
        key=lambda x: x[0]
    )

    for dist, idx in sorted_results:

        if dist < SIMILARITY_THRESHOLD:

            chunk = chunks[idx]

            if len(context) + len(chunk) < MAX_CONTEXT_CHARS:
                context += chunk + "\n"
                used_sources.add(sources[idx])
            else:
                break

    if context.strip() == "":
        print("\n⚠️ No reliable context found. Try another question.\n")
        continue

    # -------------------------------------------------
    # FINAL PROMPT
    # -------------------------------------------------
    prompt = f"""
You are QUOKKA, an expert materials science assistant.

Rules:
- Answer ONLY using the provided context.u
- Do NOT invent information.
- Be concise and scientifically accurate.
- Use bullet points when helpful.
- If unsure, say:
  "The document does not contain enough information."

Context:
{context}

Question: {query}

Answer:
"""

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1800
    ).to(device)

    # -------------------------------------------------
    # GENERATE ANSWER
    # -------------------------------------------------
    with torch.no_grad():
        outputs = llm_model.generate(
            **inputs,
            max_new_tokens=400,
            do_sample=False,
            temperature=0.2,
            top_p=0.8,
            repetition_penalty=1.2,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id
        )

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Extract answer properly
    if "Answer:" in decoded:
        answer = decoded.split("Answer:")[-1].strip()
    else:
        answer = decoded.strip()

    # -------------------------------------------------
    # PRINT OUTPUT
    # -------------------------------------------------
    print("\nAnswer:\n")
    print(answer)

    print("\nSources:")
    for src in used_sources:
        print("-", src)

    print("\n" + "-" * 50 + "\n")