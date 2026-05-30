from flask import Blueprint, request, jsonify, Response, stream_with_context
import json

from models.model_router import ask_llm_stream
import memory.chat_storage as storage
from routes.auth_middleware import login_required

chat_bp = Blueprint("chat", __name__)

# ----------------------------
# CHAT ROUTE ⚡ FAST VERSION
# ----------------------------
@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.get_json()

    message = data.get("message", "")
    model = data.get("model", "phi-2")  # 🔥 default fast model
    session_id = data.get("session_id")
    is_private = data.get("is_private", False)

    temperature = data.get("temperature", 0.7)
    memory_enabled = data.get("memory_enabled", True)

    if not message or len(message) > 4000:
        return jsonify({"response": "Message is empty or too long."}), 400

    # 🔒 FORCE NO MEMORY in private mode
    if is_private:
        memory_enabled = False

    # ----------------------------
    # RAG (DOCUMENT SEARCH) ⚡
    # ----------------------------
    doc_context_text = ""
    metadata_json = None
    
    if not is_private:
        from memory.document_store import doc_store
        # 🔥 Lazy load check: only retrieve if documents exist
        if doc_store.has_documents():
            results = doc_store.retrieve_context(message, top_k=5)
            if results:
                # Filter results by similarity threshold
                filtered_results = []
                for r in results:
                    cos_sim = 1 - (r["score"] / 2)
                    if cos_sim > 0.55: # Similarity threshold
                        filtered_results.append(r)
                        
                if filtered_results:
                    context_parts = []
                    sources_set = set()
                    avg_distance = 0.0
                    
                    for r in filtered_results:
                        context_parts.append(r["text"])
                        sources_set.add(r["source"])
                        avg_distance += r["score"]
                        
                    avg_distance /= len(filtered_results)
                    
                    # Confidence calculation: L2 distance to percentage
                    cosine_sim = 1 - (avg_distance / 2)
                    confidence_pct = max(0, round(cosine_sim * 100, 1))
                    
                    doc_context = "\n\n".join(context_parts)
                    doc_context_text = f"\nUse the provided context when relevant. If the context is insufficient, answer using general knowledge while clearly distinguishing document-derived information from model knowledge.\n\nContext:\n{doc_context}\n"
                    
                    metadata_json = {
                        "sources": list(sources_set),
                        "confidence": confidence_pct
                    }

    # ----------------------------
    # CONTEXT (LIGHTWEIGHT ONLY)
    # ----------------------------
    chat_context_lines = []

    if memory_enabled and not is_private and session_id:
        chat = storage.get_chat(session_id)
        if chat:
            messages = chat.get("messages", [])[-6:]  # 🔥 last 6 msgs for better memory
            for m in messages:
                chat_context_lines.append(f"{m['role'].capitalize()}: {m['content']}")
                
    chat_context = "\n".join(chat_context_lines)

    # ----------------------------
    # PROMPT
    # ----------------------------
    prompt = f"""You are QUOKKA, a helpful AI assistant. Answer clearly, concisely, and avoid any filler sentences.
{doc_context_text}
{chat_context}

Question:
{message}

Answer:"""

    # ----------------------------
    # STREAM RESPONSE ⚡
    # ----------------------------
    def generate():
        full_response = ""

        for chunk in ask_llm_stream(prompt, model, temperature):
            yield chunk

            if chunk.startswith("data: "):
                try:
                    payload = json.loads(chunk[6:])
                    if "text" in payload:
                        full_response += payload["text"]
                except:
                    pass
                    
        # 🔍 Append Explainability Mode
        if metadata_json:
            yield f"data: {json.dumps({'metadata': metadata_json})}\n\n"

        # 💾 SAVE ONLY NORMAL CHAT
        if not is_private and session_id:
            storage.append_message(session_id, "user", message)
            storage.append_message(session_id, "assistant", full_response)

            # Auto title
            chat = storage.get_chat(session_id)
            if chat and chat.get("title") == "New Chat":
                new_title = message[:30] + "..." if len(message) > 30 else message
                storage.update_chat_title(session_id, new_title)
                yield f"data: {json.dumps({'title': new_title})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")