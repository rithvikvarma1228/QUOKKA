import numpy as np
import faiss
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM

from pdf_reader import extract_text_from_pdfs
from chunking import chunk_text

# ----------------------------
# 1️⃣ Load embedding model (GPU)
# ----------------------------
print("Loading embedding model...")
embed_model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')

# ----------------------------
# 2️⃣ Load LLM (TinyLlama - stable on 6GB GPU)
# ----------------------------
print("Loading LLM...")
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_name)

llm_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16
).to("cuda")

# ----------------------------
# 3️⃣ Prepare Knowledge Base
# ----------------------------
print("Preparing knowledge base...")
text = extract_text_from_pdfs()
chunks = chunk_text(text)

print(f"Total chunks created: {len(chunks)}")

# Generate embeddings using GPU
embeddings = embed_model.encode(
    chunks,
    convert_to_numpy=True,
    device="cuda",
    show_progress_bar=True
).astype("float32")

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

print("Chatbot is ready!\n")

# ----------------------------
# 4️⃣ Chat Loop
# ----------------------------
while True:
    query = input("Ask a materials science question (type 'exit' to stop): ")

    if query.lower() == "exit":
        break

    # Convert question to embedding (GPU)
    query_vector = embed_model.encode(
        [query],
        convert_to_numpy=True,
        device="cuda"
    ).astype("float32")

    # Retrieve top 5 relevant chunks
    distances, indices = index.search(query_vector, 5)

    context = ""
    for idx in indices[0]:
        context += chunks[idx] + "\n"

    # Prompt template
    prompt = f"""
You are a materials science expert.

Use ONLY the provided context to answer the question clearly and concisely.

Context:
{context}

Question: {query}

Answer:
"""

    # Generate answer
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    outputs = llm_model.generate(
        **inputs,
        max_new_tokens=100,
        temperature=0.3,
        do_sample=True,
        top_p=0.9,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id
    )

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Extract clean answer
    if "Answer:" in decoded:
        answer = decoded.split("Answer:")[-1].strip()
    else:
        answer = decoded.strip()

    print("\nAnswer:\n")
    print(answer)
    print("\n" + "-" * 50 + "\n")
