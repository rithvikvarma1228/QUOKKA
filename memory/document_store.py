import os
import re
import logging
import numpy as np
import faiss
from pypdf import PdfReader
from docx import Document

class DocumentStore:
    def __init__(self, model_name="BAAI/bge-small-en-v1.5", persist_dir="memory/doc_data"):
        self.model_name = model_name
        self.model = None
        self.persist_dir = persist_dir
        if not os.path.exists(self.persist_dir):
            os.makedirs(self.persist_dir)
            
        self.index_path = os.path.join(self.persist_dir, "doc_index.faiss")
        self.chunks_path = os.path.join(self.persist_dir, "doc_chunks.npy")
        self.sources_path = os.path.join(self.persist_dir, "doc_sources.npy")
        
        self._data_loaded = False
        self.index = None
        self.chunks = []
        self.sources = []
        self.dimension = 384

    def _load_data_if_needed(self):
        if self._data_loaded:
            return
            
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            self.chunks = list(np.load(self.chunks_path, allow_pickle=True))
            self.sources = list(np.load(self.sources_path, allow_pickle=True))
            self.dimension = self.index.d
        else:
            self.dimension = 384 # Default for BAAI/bge-small-en-v1.5
            self.index = faiss.IndexFlatL2(self.dimension)
            self.chunks = []
            self.sources = []
            
        self._data_loaded = True

    def has_documents(self):
        if self._data_loaded:
            return self.index.ntotal > 0
        return os.path.exists(self.index_path)

    def get_model(self):
        from models.embedding_manager import get_embedding_model
        model = get_embedding_model(self.model_name)
        self._load_data_if_needed()
        model_dim = model.get_sentence_embedding_dimension()
        if self.index.ntotal == 0 and self.dimension != model_dim:
            self.dimension = model_dim
            self.index = faiss.IndexFlatL2(self.dimension)
        elif self.index.ntotal > 0 and self.index.d != model_dim:
            raise RuntimeError(
                f"Embedding model dimension mismatch: index has {self.index.d}d "
                f"but model '{self.model_name}' produces {model_dim}d vectors. "
                f"Delete memory/doc_data/ and re-index your documents."
            )
        return model

    def save(self):
        self._load_data_if_needed()
        faiss.write_index(self.index, self.index_path)
        np.save(self.chunks_path, np.array(self.chunks))
        np.save(self.sources_path, np.array(self.sources))

    def extract_text(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            elif ext == ".pdf":
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            elif ext == ".docx":
                doc = Document(file_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
        return text

    def chunk_text(self, text, chunk_size=400, overlap=50):
        # 🔥 Paragraph-aware semantic chunking
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # If adding this paragraph keeps us under the size limit roughly (using word count approx)
            if len((current_chunk + " " + para).split()) <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If a single paragraph is too long, split by sentences
                if len(para.split()) > chunk_size:
                    sentences = re.split(r'(?<=[.!?]) +', para)
                    temp_chunk = ""
                    for sent in sentences:
                        if len((temp_chunk + " " + sent).split()) <= chunk_size:
                            temp_chunk += (" " + sent if temp_chunk else sent)
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk)
                            temp_chunk = sent
                    current_chunk = temp_chunk
                else:
                    current_chunk = para
                    
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def process_file(self, file_path, filename):
        text = self.extract_text(file_path)
        if not text.strip():
            return False
            
        file_chunks = self.chunk_text(text)
        
        if not file_chunks:
            return False
            
        # Create embeddings in batches
        vectors = self.get_model().encode(file_chunks, batch_size=64, normalize_embeddings=True)
        vectors = np.array(vectors).astype("float32")
        
        # Add to index
        self._load_data_if_needed()
        self.index.add(vectors)
        self.chunks.extend(file_chunks)
        self.sources.extend([filename] * len(file_chunks))
        
        self.save()
        return True

    def retrieve_context(self, query, top_k=5):
        self._load_data_if_needed()
        if self.index.ntotal == 0:
            return []
            
        vec = self.get_model().encode([query], normalize_embeddings=True)
        vec = np.array(vec).astype("float32")
        
        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(vec, k)
        
        results = []
        logging.debug("--- Retrieval Debugging for Query: '%s' ---", query)
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:
                score = float(dist)
                chunk_text = self.chunks[idx]
                source = self.sources[idx]
                logging.debug("[Match] Score: %.4f | Source: %s | Chunk: %s...", score, source, chunk_text[:100])
                results.append({
                    "text": chunk_text,
                    "source": source,
                    "score": score
                })
        logging.debug("-------------------------------------------------")
                
        return results

doc_store = DocumentStore()
