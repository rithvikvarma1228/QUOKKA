import os
import threading
from flask import Flask, render_template, redirect, session
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
# WARMUP — background thread
# Runs AFTER server starts accepting requests
# so browser loads instantly
# ----------------------------------------
def warmup():
    import time
    # Small delay so Flask fully starts first
    time.sleep(1)

    print("⏳ [WARMUP] Loading models into memory...")

    # Step 1: Load embedding model (only needed for RAG/document search)
    # Skip if using Groq and no documents uploaded yet
    try:
        from memory.document_store import doc_store
        if doc_store.has_documents():
            from models.embedding_manager import get_embedding_model
            get_embedding_model("BAAI/bge-small-en-v1.5")
            print("✅ [WARMUP] Embedding model ready")
        else:
            print("✅ [WARMUP] No documents found — skipping embedding model load")
    except Exception as e:
        print(f"⚠️  [WARMUP] Embedding model failed: {e}")

    # Step 2: Load FAISS document index
    try:
        from memory.document_store import doc_store
        doc_store._load_data_if_needed()
        print("✅ [WARMUP] Document index ready")
    except Exception as e:
        print(f"⚠️  [WARMUP] Document index failed: {e}")

    print("🚀 [WARMUP] QUOKKA is fully ready!")

# ----------------------------------------
# RUN SERVER
# ----------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    # Start warmup in background AFTER Flask starts
    t = threading.Thread(target=warmup, daemon=True)
    t.start()

    print(f"🌐 Starting QUOKKA on http://localhost:{port}")
    print("⏳ Models warming up in background...")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )