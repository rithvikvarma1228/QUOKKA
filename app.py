import os
import threading
import traceback
from flask import Flask, render_template, redirect, session, jsonify
from flask_mail import Mail
from dotenv import load_dotenv
from routes.chat import chat_bp
from routes.sessions import sessions_bp
from routes.upload import upload_bp
from routes.auth import auth_bp

load_dotenv()

app = Flask(__name__)

# ----------------------------------------
# APP CONFIG
# ----------------------------------------
app.secret_key = os.environ.get("SECRET_KEY", "quokka-dev-secret")

# File upload limit — 15MB
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

# Flask-Mail config
app.config["MAIL_SERVER"]         = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"]           = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"]        = True
app.config["MAIL_USE_SSL"]        = False
app.config["MAIL_USERNAME"]       = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"]       = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = ("QUOKKA AI", os.environ.get("MAIL_USERNAME"))

mail = Mail(app)

# ----------------------------------------
# ERROR HANDLERS
# ----------------------------------------
@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large. Maximum size is 15MB."}), 413

# ----------------------------------------
# TEST EMAIL — shows exact error on screen
# Visit /test-email to debug mail issues
# Remove this route after email is confirmed
# ----------------------------------------
@app.route("/test-email")
def test_email():
    from flask_mail import Message
    try:
        print(f"[TEST] SERVER={app.config['MAIL_SERVER']}", flush=True)
        print(f"[TEST] PORT={app.config['MAIL_PORT']}", flush=True)
        print(f"[TEST] USERNAME={app.config['MAIL_USERNAME']}", flush=True)
        print(f"[TEST] PASSWORD_LEN={len(app.config['MAIL_PASSWORD'] or '')}", flush=True)
        msg = Message(
            "QUOKKA Test Email",
            recipients=["brcvarma11227@gmail.com"]
        )
        msg.body = "Test email from QUOKKA on Render. Email is working!"
        mail.send(msg)
        return "✅ EMAIL SENT — check your inbox!", 200
    except Exception as e:
        err = traceback.format_exc()
        print(f"[TEST] FAILED: {err}", flush=True)
        return f"❌ FAILED: {str(e)}\n\n{err}", 200

# ----------------------------------------
# REGISTER BLUEPRINTS
# ----------------------------------------
app.register_blueprint(chat_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(auth_bp)

# ----------------------------------------
# PAGE ROUTES
# ----------------------------------------
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

# ----------------------------------------
# WARMUP — lightweight, RAM-safe
# ----------------------------------------
def warmup():
    import time
    time.sleep(1)
    print("⏳ [WARMUP] Starting...")

    enable_rag = os.environ.get("ENABLE_RAG", "false").lower() == "true"

    if enable_rag:
        try:
            from memory.document_store import doc_store
            doc_store._load_data_if_needed()
            if doc_store.has_documents():
                from models.embedding_manager import get_embedding_model
                get_embedding_model("all-MiniLM-L6-v2")
                print("✅ [WARMUP] Embedding model + FAISS ready")
            else:
                print("✅ [WARMUP] No documents — skipping embedding load")
        except Exception as e:
            print(f"⚠️  [WARMUP] RAG warmup failed: {e}")
    else:
        print("✅ [WARMUP] RAG disabled — skipping embedding model (saves RAM)")

    print("🚀 [WARMUP] QUOKKA is ready!")

# ----------------------------------------
# RUN SERVER
# ----------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    t = threading.Thread(target=warmup, daemon=True)
    t.start()

    print(f"🌐 Starting QUOKKA on http://localhost:{port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )