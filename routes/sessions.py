import io
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

from flask import Blueprint, jsonify, request, send_file
import memory.chat_storage as storage
from memory.faiss_store import delete_session as delete_faiss_session

sessions_bp = Blueprint("sessions", __name__)

@sessions_bp.route("/api/chats", methods=["GET"])
def get_normal_chats():
    # Only return normal chats
    chats = storage.get_all_chats(include_private=False)
    return jsonify({"chats": chats})

@sessions_bp.route("/api/chat/new", methods=["POST"])
def create_chat():
    data = request.get_json() or {}
    title = data.get("title", "New Chat")
    
    # Private chats are now strictly memory-less, so we only create normal chats
    chat_id = storage.create_chat(title, is_private=False)
    return jsonify({"chat_id": chat_id, "title": title})

@sessions_bp.route("/api/chat/<chat_id>", methods=["GET"])
def get_chat(chat_id):
    chat = storage.get_chat(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    return jsonify({"chat": chat})

@sessions_bp.route("/api/chat/<chat_id>", methods=["PUT"])
def rename_chat(chat_id):
    data = request.get_json()
    new_title = data.get("title")
    if new_title:
        storage.update_chat_title(chat_id, new_title)
        return jsonify({"success": True, "title": new_title})
    return jsonify({"error": "Title is required"}), 400

@sessions_bp.route("/api/chat/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    chat = storage.get_chat(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
            
    storage.delete_chat(chat_id)
    try:
        delete_faiss_session(chat_id)
    except Exception as e:
        print(f"Failed to delete FAISS session for {chat_id}: {e}")
    return jsonify({"success": True})

@sessions_bp.route("/api/chat/<chat_id>/pin", methods=["PUT"])
def toggle_pin(chat_id):
    is_pinned = storage.toggle_pin_chat(chat_id)
    return jsonify({"success": True, "is_pinned": is_pinned})

@sessions_bp.route("/api/chats/search", methods=["GET"])
def search_chats():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"results": []})
    results = storage.search_chats(q, include_private=False)
    all_chats = storage.get_all_chats(include_private=False)
    matched = [c for c in all_chats if c["chat_id"] in results]
    return jsonify({"results": matched})

@sessions_bp.route("/api/chat/<chat_id>/export", methods=["GET"])
def export_chat(chat_id):
    fmt = request.args.get("format", "txt")
    chat = storage.get_chat(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
        
    title = chat.get("title", "Exported_Chat")
    messages = chat.get("messages", [])
    
    if fmt == "txt":
        content = f"Chat: {title}\n" + "="*40 + "\n\n"
        for m in messages:
            content += f"{m['role'].upper()}:\n{m['content']}\n\n"
        
        mem = io.BytesIO()
        mem.write(content.encode('utf-8'))
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name=f"{title}.txt", mimetype='text/plain')
        
    elif fmt == "pdf" and FPDF:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        def safe_text(txt):
            if txt is None:
                return ""
            return str(txt).encode('latin-1', 'replace').decode('latin-1')
            
        pdf.cell(200, 10, txt=safe_text(f"Chat: {title}"), ln=1, align="C")
        pdf.ln(10)
        
        for m in messages:
            role_txt = safe_text(f"{m['role'].upper()}:")
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(200, 10, txt=role_txt, ln=1)
            
            pdf.set_font("Arial", '', 11)
            content_txt = safe_text(m['content'])
            pdf.multi_cell(0, 10, txt=content_txt)
            pdf.ln(5)
            
        mem = io.BytesIO()
        pdf_out = pdf.output(dest='S')
        if isinstance(pdf_out, str):
            pdf_out = pdf_out.encode('latin-1')
        else:
            pdf_out = bytes(pdf_out)
        mem.write(pdf_out)
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name=f"{title}.pdf", mimetype='application/pdf')
        
    return jsonify({"error": "Format not supported"}), 400
