import os
import threading
import traceback
from flask import Flask, render_template, redirect, session, jsonify
from dotenv import load_dotenv
from routes.chat import chat_bp
from routes.sessions import sessions_bp
from routes.upload import upload_bp
from routes.auth import auth_bp

load_dotenv()

app = Flask(__name__)

# ── App config ────────────────────────────────────────────────────────────────
app.secret_key = os.environ.get("SECRET_KEY", "quokka-dev-secret-change-me")

# File upload limit — 15 MB
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

# ── Error handlers ────────────────────────────────────────────────────────────
@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large. Maximum size is 15 MB."}), 413

# ── Email test route ──────────────────────────────────────────────────────────
# Visit /test-email to verify Brevo API is wired up correctly.
@app.route("/test-email")
def test_email():
    try:
        from services.mail_service import _send
        to = os.environ.get("MAIL_FROM", "")
        if not to:
            return "❌ MAIL_FROM env var is not set. Add it in Render.", 200
        _send(to, "QUOKKA Admin", "QUOKKA Test Email",
              "<p style='font-family:sans-serif;color:#333'>Test email from QUOKKA — Brevo API is working!</p>")
        return f"✅ Test email sent to {to} via Brevo HTTP API — check your inbox!", 200
    except Exception as e:
        err = traceback.format_exc()
        print(f"[TEST EMAIL FAILED]\n{err}", flush=True)
        return f"❌ FAILED: {str(e)}\n\n{err}", 200

# ── Blueprints ────────────────────────────────────────────────────────────────
app.register_blueprint(chat_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(auth_bp)

# ── Page routes ───────────────────────────────────────────────────────────────
@app.route("/")
def serve_index():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("index.html")

@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect("/")
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    if "user_id" in session:
        return redirect("/")
    return render_template("signup.html")

@app.route("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")

@app.route("/reset-password")
def reset_password_page():
    return render_template("reset_password.html")

@app.route("/profile")
def profile_page():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("profile.html")

# ── Warmup ────────────────────────────────────────────────────────────────────
def warmup():
    import time
    time.sleep(1)
    print("⏳ [WARMUP] Starting...", flush=True)

    enable_rag = os.environ.get("ENABLE_RAG", "false").lower() == "true"

    if enable_rag:
        try:
            from memory.document_store import doc_store
            doc_store._load_data_if_needed()
            if doc_store.has_documents():
                from models.embedding_manager import get_embedding_model
                get_embedding_model("all-MiniLM-L6-v2")
                print("✅ [WARMUP] Embedding model + FAISS ready", flush=True)
            else:
                print("✅ [WARMUP] No documents — skipping embedding load", flush=True)
        except Exception as e:
            print(f"⚠️  [WARMUP] RAG warmup failed: {e}", flush=True)
    else:
        print("✅ [WARMUP] RAG disabled — skipping embedding model (saves RAM)", flush=True)

    print("🚀 [WARMUP] QUOKKA is ready!", flush=True)

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    threading.Thread(target=warmup, daemon=True).start()
    print(f"🌐 Starting QUOKKA on http://localhost:{port}", flush=True)

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)