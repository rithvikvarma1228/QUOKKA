import threading

class EmbeddingManager:
    _instance = None
    _lock = threading.Lock()
    _model = None
    
    @classmethod
    def get_model(cls, model_name="BAAI/bge-small-en-v1.5"):
        with cls._lock:
            if cls._model is None:
                print(f"Loading global SentenceTransformer model: {model_name}...")
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer(model_name)
            return cls._model

def get_embedding_model(model_name="BAAI/bge-small-en-v1.5"):
    return EmbeddingManager.get_model(model_name)
