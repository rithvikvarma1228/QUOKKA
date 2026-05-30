import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from memory.document_store import doc_store

upload_bp = Blueprint("upload", __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route("/api/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # 🧠 LIVE DOCUMENT INTELLIGENCE
        try:
            from models.model_router import ask_llm_json
            # Extract first 2500 characters to keep the request fast
            text = doc_store.extract_text(file_path)[:2500]
            
            prompt = f"""Analyze the following document text.
Provide a JSON response with exactly this structure:
{{
    "summary": "A 3-5 line summary of the text",
    "topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
    "questions": ["Suggested question 1?", "Suggested question 2?", "Suggested question 3?"]
}}

Document Text:
{text}"""
            insights = ask_llm_json(prompt)
            if not insights:
                insights = {
                    "summary": "Could not generate summary.",
                    "topics": [],
                    "questions": []
                }
        except Exception as e:
            print(f"Intelligence generation error: {e}")
            insights = {
                "summary": "Error generating insights.",
                "topics": [],
                "questions": []
            }
        
        # Process and add to document store in background
        import threading
        thread = threading.Thread(target=doc_store.process_file, args=(file_path, filename))
        thread.start()
        
        return jsonify({
            "success": True, 
            "message": f"File {filename} is being processed in the background.",
            "summary": insights.get("summary", ""),
            "topics": insights.get("topics", []),
            "questions": insights.get("questions", [])
        })
            
    return jsonify({"error": "File type not allowed"}), 400
