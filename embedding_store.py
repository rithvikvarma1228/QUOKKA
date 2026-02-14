import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from chunking import chunk_text
from pdf_reader import extract_text_from_pdfs

# Load embedding model
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Extract and chunk text
print("Extracting text...")
text = extract_text_from_pdfs()

print("Creating chunks...")
chunks = chunk_text(text)

print(f"Total chunks: {len(chunks)}")

# Convert chunks to embeddings
print("Generating embeddings...")
embeddings = model.encode(chunks)

# Convert to numpy array
embeddings = np.array(embeddings).astype('float32')

# Create FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)

print("Adding embeddings to FAISS index...")
index.add(embeddings)

print("FAISS index created successfully.")
print(f"Total vectors stored: {index.ntotal}")
