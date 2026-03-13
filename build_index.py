import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import os
from pypdf import PdfReader

print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

DATA_PATH = "data"

texts = []
sources = []

print("Reading PDFs...")

for filename in os.listdir(DATA_PATH):
    if filename.endswith(".pdf"):
        filepath = os.path.join(DATA_PATH, filename)
        reader = PdfReader(filepath)

        for page in reader.pages:
            text = page.extract_text()

            if text:
                text = text.replace("\n", " ").strip()
                texts.append(text)
                sources.append(filename)

print("Total pages extracted:", len(texts))

# ----------------------------
# Chunking
# ----------------------------
def chunk_text(text, size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap

    return chunks

chunks = []
chunk_sources = []

for text, src in zip(texts, sources):
    split_chunks = chunk_text(text)
    chunks.extend(split_chunks)
    chunk_sources.extend([src]*len(split_chunks))

print("Total chunks:", len(chunks))

# ----------------------------
# Embeddings
# ----------------------------
print("Generating embeddings...")
embeddings = embed_model.encode(chunks, show_progress_bar=True, normalize_embeddings=True)
embeddings = np.array(embeddings).astype("float32")

# ----------------------------
# FAISS
# ----------------------------
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# ----------------------------
# Save everything
# ----------------------------
faiss.write_index(index, "index.faiss")
np.save("chunks.npy", chunks)
np.save("sources.npy", chunk_sources)

print("\n✅ Index rebuilt with sources!")