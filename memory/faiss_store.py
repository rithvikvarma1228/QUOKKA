# NOTE: FaissStore is NOT currently wired into the active request pipeline.
# It is reserved for future per-session semantic memory — allowing the assistant
# to retrieve relevant past messages from a session via vector search rather than
# simple recency. To activate, integrate store_message() / retrieve_context()
# calls from routes/chat.py alongside or replacing the SQLite message window.
import os
import json
import numpy as np
import faiss

class FaissStore:
    def __init__(self, model_name="all-MiniLM-L6-v2", persist_dir="memory/faiss_data"):
        self.model_name = model_name
        self.model = None  # 🔥 Lazy loading
        self.persist_dir = persist_dir
        if not os.path.exists(self.persist_dir):
            os.makedirs(self.persist_dir)
        self.dimension = 384  # Hardcoded for all-MiniLM-L6-v2 to avoid loading model
        self._index_cache = {}
        self._meta_cache = {}

    def get_model(self):
        from models.embedding_manager import get_embedding_model
        return get_embedding_model(self.model_name)
        
    def _get_index_path(self, session_id):
        return os.path.join(self.persist_dir, f"{session_id}.faiss")
        
    def _get_meta_path(self, session_id):
        return os.path.join(self.persist_dir, f"{session_id}.json")
        
    def _load_index(self, session_id):
        if session_id in self._index_cache:
            return self._index_cache[session_id]
            
        index_path = self._get_index_path(session_id)
        if os.path.exists(index_path):
            index = faiss.read_index(index_path)
        else:
            index = faiss.IndexFlatL2(self.dimension)
            
        self._index_cache[session_id] = index
        return index
        
    def _save_index(self, session_id, index):
        self._index_cache[session_id] = index
        index_path = self._get_index_path(session_id)
        faiss.write_index(index, index_path)
        
    def _load_meta(self, session_id):
        if session_id in self._meta_cache:
            return self._meta_cache[session_id]
            
        meta_path = self._get_meta_path(session_id)
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
        else:
            meta = []
            
        self._meta_cache[session_id] = meta
        return meta
        
    def _save_meta(self, session_id, meta):
        self._meta_cache[session_id] = meta
        meta_path = self._get_meta_path(session_id)
        with open(meta_path, "w") as f:
            json.dump(meta, f)

    def store_message(self, session_id, role, message):
        index = self._load_index(session_id)
        meta = self._load_meta(session_id)
        
        # Create embedding
        text_to_embed = f"{role}: {message}"
        vec = self.get_model().encode([text_to_embed], normalize_embeddings=True)
        vec = np.array(vec).astype("float32")
        
        index.add(vec)
        meta.append({"role": role, "message": message})
        
        self._save_index(session_id, index)
        self._save_meta(session_id, meta)

    def retrieve_context(self, session_id, query, top_k=5):
        index = self._load_index(session_id)
        meta = self._load_meta(session_id)
        
        if index.ntotal == 0:
            return ""
            
        vec = self.get_model().encode([query], normalize_embeddings=True)
        vec = np.array(vec).astype("float32")
        
        k = min(top_k, index.ntotal)
        distances, indices = index.search(vec, k)
        
        retrieved = []
        # Sort indices to maintain conversation order
        valid_indices = [idx for idx in indices[0] if idx != -1]
        valid_indices.sort()
        
        for idx in valid_indices:
            msg = meta[idx]
            retrieved.append(f"{msg['role'].capitalize()}: {msg['message']}")
            
        return "\n".join(retrieved)

    def delete_session(self, session_id):
        if session_id in self._index_cache:
            del self._index_cache[session_id]
        if session_id in self._meta_cache:
            del self._meta_cache[session_id]
            
        index_path = self._get_index_path(session_id)
        meta_path = self._get_meta_path(session_id)
        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)

faiss_store = FaissStore()

def store_message(session_id, role, message):
    faiss_store.store_message(session_id, role, message)

def retrieve_context(session_id, query, top_k=5):
    return faiss_store.retrieve_context(session_id, query, top_k)

def delete_session(session_id):
    faiss_store.delete_session(session_id)
