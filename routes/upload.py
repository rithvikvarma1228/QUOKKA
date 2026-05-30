import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from memory.document_store import doc_store

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}
MAX_PDF_PAGES = 50
MAX_FILE_SIZE_MB = 15

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": "File type not supported. Please upload PDF, TXT, or DOCX files only."
        }), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower()

    # Save to uploads folder
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Check file size (belt and suspenders — Flask already checks MAX_CONTENT_LENGTH)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        os.remove(file_path)
        return jsonify({
            "error": f"File too large ({file_size_mb:.1f}MB). Maximum is {MAX_FILE_SIZE_MB}MB."
        }), 400

    # Check PDF page count
    if ext == "pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            if page_count > MAX_PDF_PAGES:
                os.remove(file_path)
                return jsonify({
                    "error": f"PDF has {page_count} pages. Maximum is {MAX_PDF_PAGES} pages."
                }), 400
        except Exception as e:
            os.remove(file_path)
            return jsonify({"error": f"Could not read PDF: {str(e)}"}), 400

    # Process and index the file
    try:
        success = doc_store.process_file(file_path, filename)
        if success:
            return jsonify({
                "success": True,
                "message": f"{filename} uploaded and indexed successfully",
                "filename": filename,
                "size_mb": round(file_size_mb, 2)
            })
        else:
            return jsonify({
                "error": "Could not extract text from file. File may be empty or corrupted."
            }), 400
    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500