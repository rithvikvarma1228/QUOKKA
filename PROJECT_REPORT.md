# QUOKKA — Complete Project Documentation Report

> **Generated:** June 2026  
> **Purpose:** Full technical reference for teammates, reviewers, and non-technical readers.  
> **Coverage:** Every file, every technology, every API endpoint, every security measure.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [How The App Works — Simple Explanation](#2-how-the-app-works--simple-explanation)
3. [Complete Folder Structure](#3-complete-folder-structure)
4. [Technology Stack — Deep Explanation](#4-technology-stack--deep-explanation)
5. [All Dependencies Explained](#5-all-dependencies-explained)
6. [Database Schema](#6-database-schema)
7. [API Endpoints — Complete Reference](#7-api-endpoints--complete-reference)
8. [Authentication System — Full Explanation](#8-authentication-system--full-explanation)
9. [Chat System — Full Explanation](#9-chat-system--full-explanation)
10. [RAG Pipeline — Full Explanation](#10-rag-pipeline--full-explanation)
11. [Frontend Explanation](#11-frontend-explanation)
12. [Security Features](#12-security-features)
13. [Environment Variables](#13-environment-variables)
14. [Deployment Plan](#14-deployment-plan)
15. [Known Limitations & Future Improvements](#15-known-limitations--future-improvements)
16. [Glossary](#16-glossary)

---

## 1. Project Overview

### What is QUOKKA?

QUOKKA is a **self-hosted AI chat assistant** — a web application you run on a server that lets users have conversations with powerful AI language models directly in their browser. Think of it as your own private version of ChatGPT, but with extra capabilities like document search, private mode, and full control over where your data lives.

The name "QUOKKA" is styled entirely in uppercase, referencing the small, cheerful marsupial — reflecting the project's friendly, approachable design aesthetic.

### What problem does it solve?

Most AI chat tools (ChatGPT, Claude, Gemini) have three major limitations:
1. **Privacy** — your conversations are stored on someone else's servers.
2. **Document grounding** — they can't answer questions specifically about *your* private documents unless you pay for premium features.
3. **Cost** — per-token billing at scale becomes expensive quickly.

QUOKKA solves all three by giving you a self-hosted assistant where:
- You control the database — your chats stay on your server.
- You can upload PDFs, DOCX files, and text files, and the AI will search them for relevant answers.
- You use the **Groq API**, which is currently free and extremely fast.

### Who is it built for?

- **Developers** who want a fast, extensible, self-hostable AI assistant.
- **Students and researchers** who want to chat with their documents (research papers, textbooks).
- **Small teams** who need a shared internal AI assistant with user accounts.
- **Privacy-conscious users** who do not want their chat history stored on third-party servers.

### What can a user do with it?

- **Register** with email, verify with a 6-digit OTP code, then log in.
- **Chat** with AI using multiple models (fast or smart, their choice).
- **Upload documents** (PDF, DOCX, TXT) and ask questions about them — the AI will cite sources and show a confidence percentage.
- **Enable Private Mode** — chat without anything being saved to the server.
- **Export conversations** as plain text (`.txt`) or formatted PDF.
- **Pin important chats**, rename them, search through all chats.
- **Manage their profile** — change display name, change password, or delete their account.
- **Recover a forgotten password** via a secure email link.

### What makes it different from a regular chatbot?

| Feature | Regular Chatbot | QUOKKA |
|---|---|---|
| Self-hosted | ❌ | ✅ |
| Document RAG | Limited | ✅ Full PDF/DOCX/TXT |
| Private mode (zero server storage) | ❌ | ✅ |
| Email verification | ❌ | ✅ OTP-based |
| Export chat as PDF | ❌ | ✅ |
| Open source / free | Limited | ✅ MIT License |
| Streaming word-by-word | Varies | ✅ SSE streaming |
| Source citation with confidence % | ❌ | ✅ |

---

## 2. How The App Works — Simple Explanation

### The Complete User Journey

**Step 1: User opens the browser**  
They navigate to the QUOKKA URL (e.g., `http://localhost:8000`). The server detects they have no active session and redirects them to `/login`.

**Step 2: User signs up with email**  
They click "Don't have an account? Sign up" and fill in:
- Full name (minimum 2 characters)
- Email address (validated by the server)
- Password (minimum 8 characters, must contain at least one number)

**Step 3: User gets OTP on email**  
The server creates their account in the database (marked as *unverified*), generates a random 6-digit number (e.g., `482931`), stores it with a 10-minute expiry, and sends it to their email via the Brevo email API. The user sees a panel with 6 individual boxes to type the code.

**Step 4: User verifies and logs in**  
The user types the 6-digit code. The server checks:
- Is it the right code? (max 5 attempts before account is wiped)
- Has it expired? (10-minute window)

If valid, the account is marked **verified**, the session is created (the user is now "logged in"), and a welcome email is sent.

**Step 5: User types a question**  
The main chat page loads. The user sees a dark-themed interface with a sidebar listing their past conversations. They type a message in the text box at the bottom and press Enter or click the send button.

**Step 6: App sends it to Groq API**  
The JavaScript in the browser sends the message to the server via a `POST /api/chat` request. The server:
- Checks if the user is logged in (session validation)
- Optionally retrieves relevant text from any uploaded documents (RAG)
- Optionally retrieves the last 6 messages from that chat (memory context)
- Assembles a full prompt and sends it to the **Groq API** via an HTTP request

**Step 7: AI generates response**  
Groq's servers run the LLaMA model and generate a response. Instead of waiting for the entire response to be ready, Groq streams it back token by token (a "token" is roughly a word or part of a word).

**Step 8: Response streams back word by word**  
Each small piece (token) arrives as a Server-Sent Event (SSE). The server forwards each piece to the browser. The browser appends each piece to the chat bubble in real time — the user sees the text appearing word by word, just like ChatGPT.

**Step 9: User sees the answer**  
When all tokens have arrived, the browser renders the final response as formatted Markdown (so headings, bold text, code blocks, bullet lists all look proper). Action buttons appear under the response: Copy and Regenerate.

---

### What happens when a user uploads a PDF

1. User clicks the **paperclip icon** in the chat input area.
2. Browser opens a file picker. User selects a PDF, DOCX, or TXT file (max 15 MB, max 50 pages for PDF).
3. The file is sent to `POST /api/upload`.
4. The server:
   - Validates the file type and size
   - Saves the file to the `uploads/` folder
   - Reads all the text out of the file (using `pypdf` for PDFs, `python-docx` for DOCX)
   - Splits the text into overlapping chunks of ~400 words each (max 100 chunks)
   - Runs each chunk through the `BAAI/bge-small-en-v1.5` embedding model to convert it into a list of 384 numbers (a "vector")
   - Saves all vectors into a FAISS index file on disk
5. The chat input shows "filename.pdf (Indexed ✓)"

From this point on, every question the user asks will first search the document. If relevant chunks are found (above a 55% similarity threshold), they are injected into the prompt so the AI can use them to answer.

---

### What happens when Private Mode is on

1. User toggles the **Private Chat** switch in the header.
2. The sidebar blurs and becomes unclickable.
3. A red warning banner appears: "Private Mode Active (Messages are not saved)".
4. The JavaScript keeps a `privateMessages` array in browser memory only — this is never sent to the server for storage.
5. When the user closes the tab, all private messages are permanently gone.
6. Document RAG is also disabled in private mode.

---

### What happens when user exports a chat

1. User opens the Settings modal (gear icon) and clicks **TXT** or **PDF**.
2. The browser opens `GET /api/chat/{id}/export?format=txt` (or `?format=pdf`) in a new tab.
3. The server fetches the full chat from the SQLite database.
4. For TXT: writes the conversation as plain text into a `BytesIO` buffer and returns it as a file download.
5. For PDF: uses the `FPDF2` library to create a formatted PDF document with bold role labels and wraps long text into multi-line cells.
6. The browser automatically downloads the file.

---

## 3. Complete Folder Structure

```
QUOKKA/
├── app.py
├── requirements.txt
├── .env
├── .gitignore
├── gunicorn.conf.py
├── render.yaml
├── README.md
├── PROJECT_REPORT.md
│
├── routes/
│   ├── auth.py
│   ├── auth_middleware.py
│   ├── chat.py
│   ├── sessions.py
│   └── upload.py
│
├── memory/
│   ├── chat_storage.py
│   ├── document_store.py
│   ├── faiss_store.py
│   ├── pinecone_store.py
│   ├── doc_data/           (auto-created, git-ignored)
│   └── faiss_data/         (per-session FAISS files, git-ignored)
│
├── models/
│   ├── model_router.py
│   └── embedding_manager.py
│
├── services/
│   ├── __init__.py
│   └── mail_service.py
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   └── profile.html
│
├── static/
│   ├── css/
│   │   ├── styles.css
│   │   └── auth.css
│   └── js/
│       ├── app.js
│       └── auth.js
│
├── data/                   (auto-created, git-ignored)
│   ├── chats.db
│   └── chats.json.bak
│
├── uploads/                (auto-created, git-ignored)
└── sessions.db             (Flask session store, git-ignored)
```

---

### File-by-File Breakdown

---

#### `app.py`
- **What it is:** The main Flask application entry point. This is the first file Python runs when the app starts.
- **What it does:**
  - Creates the Flask `app` object
  - Loads environment variables from `.env`
  - Sets the secret key (used to sign session cookies) and the 15 MB file upload limit
  - Registers all four Blueprints (auth, chat, sessions, upload) — connecting their routes to the app
  - Defines the six page routes (`/`, `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/profile`) — these serve HTML pages
  - Has a `/test-email` debug route to confirm the email service works
  - Has a `warmup()` function that runs in a background thread at startup — if RAG is enabled, it pre-loads the embedding model so the first upload isn't slow
  - When run directly (`python app.py`), starts the Flask development server on the port from `.env`
- **Talks to:** `routes/chat.py`, `routes/sessions.py`, `routes/upload.py`, `routes/auth.py`, `services/mail_service.py`, `models/embedding_manager.py`, `memory/document_store.py`
- **Why needed:** Without this file, nothing works. It is the glue that binds all parts of the application together.

---

#### `requirements.txt`
- **What it is:** A plain text file listing every Python package this project needs.
- **What it does:** When you run `pip install -r requirements.txt`, Python installs all listed packages from PyPI (Python's package registry). The first line `--extra-index-url https://download.pytorch.org/whl/cpu` tells pip to also look in PyTorch's package registry to get the CPU-only version of PyTorch (smaller, no GPU needed).
- **Talks to:** Nothing at runtime — it is only used during installation.
- **Why needed:** Without it, developers and deployment servers have no way to know which packages to install.

---

#### `.env`
- **What it is:** A file containing secret configuration values that should never be committed to version control.
- **What it does:** Stores: `SECRET_KEY`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `BASE_URL`, `FLASK_ENV`, `PORT`, `GROQ_API_KEY`.
- **Talks to:** `app.py` loads it with `python-dotenv`; all other files read from `os.environ`.
- **Why needed:** Separates secrets from code. If this file were in Git, anyone with access to the repository could steal the API keys and send emails from your account.
- **⚠️ Important:** This file is listed in `.gitignore` and should never be pushed to GitHub.

---

#### `.gitignore`
- **What it is:** A Git configuration file that tells Git which files to ignore.
- **What it does:** Prevents `.env`, `venv/`, `__pycache__/`, `*.pyc`, `*.db`, `sessions.db`, `memory/faiss_data/`, `data/`, `uploads/`, `*.npy`, `*.faiss`, and `.DS_Store` from being committed to the repository.
- **Talks to:** Git only.
- **Why needed:** Prevents secrets, large binary files, and auto-generated caches from polluting the repository.

---

#### `gunicorn.conf.py`
- **What it is:** Configuration file for the Gunicorn production web server.
- **What it does:** Sets three parameters:
  - `workers = 1` — run only one worker process (appropriate for a free Render instance with limited RAM, especially since the embedding model is large)
  - `worker_class = "sync"` — use the standard synchronous worker (SSE streaming requires `sync` or `eventlet`)
  - `timeout = 120` — kill a worker if it hasn't responded in 120 seconds (prevents hung processes)
- **Talks to:** Gunicorn reads this file when started with `--config gunicorn.conf.py`.
- **Why needed:** Without it, Gunicorn would use defaults that might timeout during long AI generations.

---

#### `render.yaml`
- **What it is:** A deployment configuration file for the Render cloud hosting platform.
- **What it does:** Tells Render to:
  - Create a web service named `quokka-ai`
  - Use Python runtime
  - Build by running `pip install -r requirements.txt`
  - Start by running `gunicorn app:app --config gunicorn.conf.py`
  - Use Python version 3.10.0
- **Talks to:** Render's deployment pipeline reads this file automatically.
- **Why needed:** Allows one-click deployment to Render — instead of manually configuring everything in the Render dashboard.

---

#### `README.md`
- **What it is:** The project's public-facing documentation shown on GitHub.
- **What it does:** Explains what QUOKKA is, lists features, shows the tech stack, explains setup steps, documents all API endpoints, and explains deployment.
- **Talks to:** Nobody — it is documentation for humans.
- **Why needed:** Essential for any open-source project so others can understand and use it.

---

#### `routes/auth.py`
- **What it is:** The complete authentication system — register, verify OTP, resend OTP, login, logout, forgot password, reset password, profile management, and account deletion.
- **What it does:**
  - `POST /api/auth/register` — validates name/email/password, creates user, sends OTP
  - `POST /api/auth/verify-otp` — checks OTP, marks user verified, creates session
  - `POST /api/auth/resend-otp` — generates new OTP, sends it, resets attempt counter
  - `POST /api/auth/login` — checks password hash, creates session
  - `POST /api/auth/logout` — clears session
  - `POST /api/auth/forgot-password` — generates reset token, sends email link
  - `POST /api/auth/reset-password` — validates token, updates password hash
  - `GET /api/auth/me` — returns currently logged-in user info
  - `GET /api/auth/profile` — returns full profile + chat count
  - `PUT /api/auth/profile` — updates display name
  - `PUT /api/auth/change-password` — verifies current password, updates hash
  - `DELETE /api/auth/account` — deletes user + all their chats
- **Talks to:** `memory/chat_storage.py` (all database operations), `services/mail_service.py` (sending emails), `routes/auth_middleware.py` (login_required decorator)
- **Why needed:** Without this file, there is no user system — anyone could access the app without an account.

---

#### `routes/auth_middleware.py`
- **What it is:** A tiny utility file containing one function: the `login_required` decorator.
- **What it does:**
  ```python
  def login_required(f):
      @wraps(f)
      def decorated(*args, **kwargs):
          if "user_id" not in session:
              return jsonify({"error": "Unauthorized", "redirect": "/login"}), 401
          return f(*args, **kwargs)
      return decorated
  ```
  When you put `@login_required` above a route function, it wraps that function. Before the route runs, it checks if `user_id` is in the Flask session. If not, it returns a 401 Unauthorized response immediately. If yes, it proceeds normally.
- **Talks to:** Used by `routes/auth.py`, `routes/chat.py`, `routes/sessions.py`, `routes/upload.py`.
- **Why needed:** Prevents unauthenticated users from accessing chat, upload, and session endpoints.

---

#### `routes/chat.py`
- **What it is:** The core of the application — the route that handles every chat message.
- **What it does:**
  1. Receives `POST /api/chat` with message, model, session_id, is_private, temperature, memory_enabled
  2. Validates the message (not empty, not over 4,000 characters)
  3. If not private and documents exist: runs RAG retrieval, filters results by 55% similarity threshold, calculates confidence percentage
  4. If memory is enabled: fetches the last 6 messages from the chat history
  5. Assembles the full prompt (system instruction + document context + chat history + user question)
  6. Calls `ask_llm_stream()` which streams tokens from Groq
  7. Yields each token as an SSE event (`data: {"text": "..."}`)
  8. After the full response: if documents were used, yields a metadata event with source filenames and confidence score
  9. If not private: saves user message and AI response to SQLite, auto-titles the chat
- **Talks to:** `models/model_router.py` (Groq API), `memory/document_store.py` (RAG), `memory/chat_storage.py` (saving messages), `routes/auth_middleware.py`
- **Why needed:** Without this file, there is no chat functionality.

---

#### `routes/sessions.py`
- **What it is:** The chat session management routes — creating, listing, loading, renaming, deleting, pinning, searching, and exporting chats.
- **What it does:**
  - `GET /api/chats` — returns all non-private chats for the sidebar
  - `POST /api/chat/new` — creates a new chat row in the database
  - `GET /api/chat/<id>` — returns a chat with its full message history
  - `PUT /api/chat/<id>` — renames a chat
  - `DELETE /api/chat/<id>` — deletes a chat and its FAISS session data
  - `PUT /api/chat/<id>/pin` — toggles pin/unpin
  - `GET /api/chats/search` — searches chats by title or message content
  - `GET /api/chat/<id>/export` — exports as TXT or PDF using FPDF2
- **Talks to:** `memory/chat_storage.py` (all database operations), `memory/faiss_store.py` (deletes FAISS data on chat delete)
- **Why needed:** Without this file, users cannot manage their conversations.

---

#### `routes/upload.py`
- **What it is:** The file upload endpoint.
- **What it does:**
  1. Receives `POST /api/upload` with a multipart file
  2. Validates: file must be present, not empty, must be PDF/TXT/DOCX extension
  3. Sanitizes the filename with `secure_filename()` to prevent path traversal attacks
  4. Saves to `uploads/` directory (creates it if needed)
  5. Double-checks file size (≤15 MB)
  6. For PDFs: reads page count with pypdf; rejects if > 50 pages
  7. Calls `doc_store.process_file()` to extract text, chunk it, embed it, and save to FAISS
  8. Returns success with filename and size
- **Talks to:** `memory/document_store.py`, `routes/auth_middleware.py`
- **Why needed:** Without this file, RAG document upload does not work.

---

#### `memory/chat_storage.py`
- **What it is:** The complete data access layer for the SQLite database. All reading and writing of chats, messages, and users goes through this file.
- **What it does:** Defines and initializes the database schema, then provides functions for every database operation:
  - **Chat operations:** `create_chat`, `get_all_chats`, `get_chat`, `update_chat_title`, `append_message`, `delete_chat`, `toggle_pin_chat`, `search_chats`, `update_summary`, `trim_messages`
  - **User operations:** `create_user`, `get_user_by_email`, `get_user_by_id`, `get_user_by_reset_token`, `set_user_otp`, `increment_otp_attempts`, `verify_user_email`, `set_reset_token`, `update_password`, `clear_reset_token`, `delete_unverified_user`, `update_user_name`, `get_user_chat_count`, `delete_user_account`
  - Also handles migration from an old JSON-based storage format to SQLite on first run
  - Called `init_storage()` automatically on import to create tables if they don't exist
- **Talks to:** SQLite via Python's built-in `sqlite3` library. The database file is at `data/chats.db`.
- **Why needed:** Every feature that persists data relies on this file.

---

#### `memory/document_store.py`
- **What it is:** The RAG (Retrieval-Augmented Generation) document processing and retrieval engine.
- **What it does:**
  - `extract_text(file_path)` — reads raw text from PDF (pypdf), DOCX (python-docx), or TXT files
  - `chunk_text(text, chunk_size=400, overlap=50)` — splits text into overlapping paragraph-aware chunks of ~400 words
  - `process_file(file_path, filename)` — full ingestion pipeline: extract → chunk → embed → add to FAISS → save to disk. Limits to 100 chunks max per document.
  - `retrieve_context(query, top_k=5)` — embeds the query, searches FAISS for the top-5 closest chunks, returns their text, source filename, and L2 distance score
  - `has_documents()` — quickly checks if any documents have been indexed
  - Uses `BAAI/bge-small-en-v1.5` (via `embedding_manager.py`) instead of the class-default `all-MiniLM-L6-v2`
  - Persists the FAISS index and chunk arrays to `memory/doc_data/`
- **Talks to:** `models/embedding_manager.py` (to get the embedding model), `faiss` library (vector operations), `pypdf` and `python-docx` (text extraction)
- **Why needed:** This is the intelligence behind document Q&A. Without it, uploaded files would not influence AI responses at all.

---

#### `memory/faiss_store.py`
- **What it is:** A per-session vector store for conversation memory (currently NOT wired into the active pipeline).
- **What it does:** Implements `FaissStore` — a class that would store each chat message as a vector and retrieve semantically relevant past messages. Has a clear comment at the top:
  > "NOTE: FaissStore is NOT currently wired into the active request pipeline. It is reserved for future per-session semantic memory."
  
  Currently, `delete_session()` IS used by `routes/sessions.py` to clean up FAISS files when a chat is deleted. The `store_message()` and `retrieve_context()` functions are implemented but not called from anywhere in the active pipeline.
  
  The `memory/faiss_data/` directory contains `.faiss` and `.json` files named by chat UUID — these were created during development/testing.
- **Talks to:** `models/embedding_manager.py` (lazy-loaded), FAISS library
- **Why needed:** For cleanup on chat deletion (active use); for future semantic memory (planned use).

---

#### `memory/pinecone_store.py`
- **What it is:** A placeholder stub for a future Pinecone-based vector store.
- **What it does:** Defines `PineconeStore` with empty `store_message()` and `retrieve_context()` methods. All methods have `# TODO` comments explaining what they would do. Nothing is implemented. This file is currently not imported or used anywhere in the active application.
- **Talks to:** Nothing (stub only).
- **Why needed:** Reserved for a future migration from local FAISS to the Pinecone cloud vector database.

---

#### `models/model_router.py`
- **What it is:** The Groq API client — the file that sends prompts to the AI and returns responses.
- **What it does:**
  - Defines a mapping from internal model names to Groq model IDs:
    ```python
    GROQ_MODEL_MAP = {
        "llama3.1:8b":  "llama-3.1-8b-instant",
        "llama3.1:70b": "llama-3.3-70b-versatile",
    }
    ```
  - `ask_llm_stream(prompt, model, temperature)` — sends a POST request to `https://api.groq.com/openai/v1/chat/completions` with `"stream": True`. Iterates over the response line by line. Each line that starts with `data: ` and contains a delta token is yielded as `data: {"text": "..."}`. When `[DONE]` is received, iteration stops.
  - `ask_llm_json(prompt, model, temperature)` — same request but with `"stream": False`. Returns the complete response parsed as JSON. (Used for non-streaming calls, though currently only `ask_llm_stream` is called from the chat route.)
- **Talks to:** The Groq API over HTTPS via the `requests` library.
- **Why needed:** Without this file, the app cannot communicate with the AI model.

---

#### `models/embedding_manager.py`
- **What it is:** A singleton manager for the sentence embedding model, ensuring it is loaded only once.
- **What it does:**
  - Uses a class-level variable and a threading lock to ensure only one instance of `SentenceTransformer` is ever created, even if multiple threads call `get_model()` simultaneously.
  - Default model: `BAAI/bge-small-en-v1.5` (overridable by passing a different name).
  - Lazy-loads the model on first call — avoids loading a large model at startup if it's not needed.
- **Talks to:** `sentence_transformers` library (which downloads the model from HuggingFace on first use).
- **Why needed:** Loading a SentenceTransformer model takes several seconds and uses significant RAM. Without this singleton, every RAG request would re-load the model.

---

#### `services/__init__.py`
- **What it is:** An empty Python file (2 bytes) that marks the `services/` directory as a Python package.
- **What it does:** Allows Python to import from `services.mail_service` using package syntax.
- **Talks to:** Nothing.
- **Why needed:** Python requires a `__init__.py` file in a directory for it to be treated as an importable package.

---

#### `services/mail_service.py`
- **What it is:** The email sending service, implemented using the **Brevo HTTP API** (not SMTP).
- **What it does:**
  - `_send(to_email, to_name, subject, html_body)` — core function. Reads `BREVO_API_KEY` and `MAIL_FROM` from environment. Constructs a JSON payload and POSTs it to `https://api.brevo.com/v3/smtp/email`. Raises a `RuntimeError` if the API returns a non-2xx response.
  - `_wrap(body)` — wraps any HTML content in a full email template with the QUOKKA brand (dark background, lime-green heading, proper HTML structure).
  - `send_otp_email(email, name, otp)` — sends the 6-digit verification code email with a styled OTP display box.
  - `send_reset_email(email, name, reset_link)` — sends the password reset email with a styled "Reset Password" button linking to the reset URL.
  - `send_welcome_email(email, name)` — sends a welcome email after successful OTP verification.
  - **Note:** The `.env` file still has `MAIL_SERVER/MAIL_PORT/MAIL_USERNAME/MAIL_PASSWORD` (Gmail SMTP settings) but the actual code uses only Brevo HTTP API. The Gmail settings are legacy and not used by the current code. `BREVO_API_KEY` and `MAIL_FROM` are what the production code actually needs.
- **Talks to:** Brevo's API over HTTPS (via `requests`). Called from `routes/auth.py`.
- **Why needed:** Email verification and password reset are impossible without this service.

---

#### `templates/index.html`
- **What it is:** The main chat page — the primary interface users see after logging in.
- **What it does:** Defines the full HTML structure:
  - **Sidebar** (left): "New Chat" button, search box, chat list (dynamically populated by JS), sidebar footer with user avatar/username, settings button, and logout button.
  - **Main content** (right): header with model selector dropdown (`LLaMA 3.1 8B ⚡ Fast` / `LLaMA 3.3 70B 🔥 Smart`), export TXT/PDF buttons, Private Chat toggle. Below the header: private mode warning banner (hidden by default), chat messages area, and at the bottom: file upload button (paperclip icon), text input textarea, and send button.
  - **Settings Modal**: slider for Temperature (0–1), toggle for Memory Context, and a model guide text.
  - Loads `Inter` font from Google Fonts, Phosphor Icons, `styles.css`, `marked.min.js` (for Markdown), and `app.js`.
- **Talks to:** `static/css/styles.css`, `static/js/app.js`
- **Why needed:** Without this HTML structure, there is no user interface for the chat.

---

#### `templates/login.html`
- **What it is:** The login page.
- **What it does:** Contains two cards (only one visible at a time):
  - **Login card**: email + password fields, login button, "Forgot password?" and "Sign up" links. If the account is unverified, a "Verify my email instead" button appears that triggers the OTP card.
  - **OTP card**: 6 individual digit boxes, Verify button, Resend OTP button. Appears when user needs to verify their email.
  - Inline `<script>` handles `doLogin()`, `showOTPPanel()`, `doVerify()`, `doResend()`, `backToLogin()`.
- **Talks to:** `static/css/auth.css`, `static/js/auth.js`
- **Why needed:** Entry point for returning users.

---

#### `templates/signup.html`
- **What it is:** The registration page.
- **What it does:** Two cards (one visible at a time):
  - **Registration card**: name, email, password (with strength bar), confirm password fields. On submit, calls `POST /api/auth/register`.
  - **OTP card**: same 6-digit boxes as login page. On submit, calls `POST /api/auth/verify-otp`. Shows resend button with 60-second countdown.
  - Includes real-time password strength bar powered by `auth.js`'s `updateStrength()` function.
- **Talks to:** `static/css/auth.css`, `static/js/auth.js`
- **Why needed:** Entry point for new users.

---

#### `templates/forgot_password.html`
- **What it is:** The "Forgot Password" page.
- **What it does:** Single email input field. On submit, calls `POST /api/auth/forgot-password`. Always shows the same success message regardless of whether the email exists (to prevent email enumeration). The form hides itself and shows a "check your inbox" message after submission.
- **Talks to:** `static/css/auth.css`, `static/js/auth.js`
- **Why needed:** Password recovery flow is impossible without this page.

---

#### `templates/reset_password.html`
- **What it is:** The password reset page. Users land here by clicking the link in their reset email.
- **What it does:** Extracts the `?token=...` from the URL using `URLSearchParams`. If no token, shows an error immediately. Otherwise shows two password fields with strength bar. On submit, sends `POST /api/auth/reset-password` with the token and new password. On success, redirects to `/login` after 2.5 seconds.
- **Talks to:** `static/css/auth.css`, `static/js/auth.js`
- **Why needed:** Without this page, users who click the reset link would see nothing.

---

#### `templates/profile.html`
- **What it is:** The user profile management page.
- **What it does:** A full-page layout with the same sidebar as `index.html` (with navigation but no chat list). Contains five sections:
  1. **Avatar & Name header** — large letter avatar, display name, email, member-since date (loaded from API)
  2. **Personal Information** — edit display name (email is disabled/read-only), Save button
  3. **Change Password** — current password, new password (with strength bar), confirm password
  4. **Your Activity** — stats grid: Total Chats, Member Since, Account Status (Verified ✓)
  5. **Danger Zone** — Delete Account button (with a confirmation modal)
  - A global 401 interceptor redirects to `/login` on any unauthorized response.
- **Talks to:** `static/css/styles.css`, `static/js/auth.js` (for `putJson`, `togglePw`, etc.)
- **Why needed:** Gives users control over their account without going to the chat page.

---

#### `static/js/app.js`
- **What it is:** The main frontend JavaScript file — controls everything that happens on the chat page.
- **What it does:** (619 lines)
  - On `DOMContentLoaded`: grabs all DOM element references, sets up all event listeners.
  - `renderMarkdown(text)` — wraps `marked.parse()` with a fallback HTML-escaping function.
  - Settings modal open/close, temperature slider update, export button clicks.
  - `loadSessions(query)` — fetches chat list from the API and calls `renderSessions()`.
  - `renderSessions(sessions)` — dynamically builds the sidebar chat list with pin/rename/delete buttons. Uses `textContent` (not `innerHTML`) for titles to prevent XSS.
  - `startNewChat()` — creates a new chat via API, sets `currentSessionId` only after server responds (prevents race conditions).
  - `switchSession(id)` — loads a specific chat's history and renders all messages.
  - `updatePrivacyMode(isPrivate)` — toggles the `privacy-mode` CSS class, blurs sidebar, clears messages.
  - File upload handler — POSTs file to `/api/upload`, shows status in the indicator.
  - `sendMessage(text)` — the heart of the app:
    - Adds user message to the UI
    - Creates an `AbortController` for stream cancellation
    - Sends POST to `/api/chat` with all settings
    - Reads the streaming response using `ReadableStream` and `TextDecoder`
    - Buffers partial SSE events across chunks
    - Updates the bot bubble live as tokens arrive (`textContent` during streaming for performance)
    - After stream completes, re-renders with `renderMarkdown()` for proper formatting
    - Handles metadata events (sources + confidence), title events, error events
  - `addMessage(text, role)` — renders a message bubble (bot messages use `innerHTML` + `renderMarkdown`, user messages use `textContent` to prevent XSS).
  - `addMessageActions(messageDiv, text)` — attaches Copy and Regenerate buttons to bot messages.
  - Init: fetches `/api/auth/me` to populate sidebar username/avatar. Sets up logout button. Overrides `window.fetch` globally so any 401 response triggers a redirect to `/login`.
- **Talks to:** All API endpoints via `fetch()`. Reads the HTML DOM.
- **Why needed:** Without this file, the page is a static HTML document with no behavior.

---

#### `static/js/auth.js`
- **What it is:** A shared utility library for all authentication pages.
- **What it does:** (149 lines)
  - `postJson(url, data)` / `putJson(url, data)` — wrapper functions that set `Content-Type: application/json` and parse the JSON response. Handle network errors gracefully.
  - `showError(id, msg)` / `showSuccess(id, msg)` / `clearAlert(id)` — show/hide styled alert boxes.
  - `togglePw(inputId, iconId)` — toggles a password field between `type="password"` and `type="text"`, updates the eye icon.
  - `strengthScore(pw)` — returns 0–3 score based on length, contains digit, contains special char, length ≥ 12.
  - `updateStrength(pw, fillId, textId)` — updates a password strength bar's width and color.
  - `setupOTP(containerId)` — wires up the 6-box OTP input: auto-focus next box on input, backspace goes to previous box, paste fills all boxes at once.
  - `getOTP(containerId)` — collects all 6 digit values and returns them as a single string.
  - `startCountdown(btnId, secs)` — disables the Resend button and counts down from 60 seconds.
  - `setLoading(btnId, spinnerId, loading)` — disables a button and shows/hides a spinner.
- **Talks to:** No API calls directly — provides helpers used by inline scripts in auth HTML pages.
- **Why needed:** Eliminates code duplication across `login.html`, `signup.html`, `forgot_password.html`, `reset_password.html`, and `profile.html`.

---

#### `static/css/styles.css`
- **What it is:** The main application stylesheet (887 lines).
- **What it does:** Defines the complete visual design of the chat interface:
  - CSS custom properties (`:root`) for the premium dark theme: `--bg-main: #0d0d0d`, `--accent-color: #d9f95d` (lime-green)
  - App container with a subtle grid background pattern
  - Sidebar styles: blurred glassmorphism background, chat item hover effects, pinned state
  - Chat message styles: `slideUp` animation, bot messages left-aligned with lime avatar, user messages right-aligned
  - Markdown rendering styles: proper `<h1>`–`<h4>`, `<ul>`, `<ol>`, `<code>`, `<pre>`, `<blockquote>`, `<table>`, `<hr>` styling inside `.msg-bubble`
  - Message action bar: copy and regenerate buttons that fade in on hover
  - Input area: frosted glass textarea box with lime-green glow on focus
  - Settings modal: overlay with blur, scale-in animation
  - Private mode: blurs and disables the sidebar, shows red warning banner
  - RAG metadata block: styled source list and confidence score below AI responses
  - Typing indicator: pulsing "Thinking..." animation
  - Responsive breakpoint at 768px: hides sidebar, adjusts paddings
- **Talks to:** Referenced by `templates/index.html` and `templates/profile.html`.
- **Why needed:** Without this file, the app would be an unstyled HTML document.

---

#### `static/css/auth.css`
- **What it is:** The stylesheet for all authentication pages (280 lines).
- **What it does:** Defines the auth-specific design:
  - Dark background (`#080808`) with a subtle grid pattern using the lime-green color
  - Centered card layout (`max-width: 420px`) with border and box shadow
  - Field styles: dark inputs, lime-green focus border
  - Password visibility toggle button
  - Password strength bar (animated width + color)
  - OTP boxes: 6 individual square inputs with monospace font, focus border
  - Spinner animation for loading states
  - Alert boxes (red for error, green for success)
  - Resend countdown button styles
  - Responsive: smaller padding on mobile
- **Talks to:** Referenced by `login.html`, `signup.html`, `forgot_password.html`, `reset_password.html`.
- **Why needed:** The auth pages need different styling from the main chat interface — a centered card layout vs. a full-screen split-panel layout.

---

#### `data/chats.db`
- **What it is:** The main SQLite database file.
- **What it does:** Stores all persistent data: user accounts, chat sessions, and all messages.
- **Talks to:** Accessed exclusively through `memory/chat_storage.py`.
- **Why needed:** This IS the data layer of the entire app.

---

#### `data/chats.json.bak`
- **What it is:** A backup of the old JSON-based chat storage (before the migration to SQLite).
- **What it does:** Nothing active — it is a legacy file created by the migration code in `chat_storage.py`. When the app first ran after switching from JSON to SQLite, it migrated all existing chats and renamed the JSON file with a `.bak` extension to avoid re-migrating on the next startup.
- **Why needed:** Historical artifact; safe to delete if you want to clean up.

---

#### `memory/faiss_data/*.faiss` and `memory/faiss_data/*.json`
- **What they are:** Per-session FAISS index files and their metadata.
- **What they do:** Each pair of files is named after a chat UUID. The `.faiss` file is the binary vector index; the `.json` file maps vector indices to message role/content. These were created by `faiss_store.py` during testing.
- **Why they exist:** Left over from development. They are listed in `.gitignore` and would not be in a clean repository.

---

#### `sessions.db`
- **What it is:** Flask's server-side session storage database.
- **What it does:** When Flask uses server-side sessions (the default), it stores session data (like `user_id`, `user_email`, `user_name`) in this SQLite file keyed by a session cookie that the user's browser holds.
- **Why needed:** Without it, login sessions could not persist across page refreshes.

---

## 4. Technology Stack — Deep Explanation

---

### Flask

**What is Flask?**  
Flask is a lightweight web framework for Python. A web framework provides the scaffolding to receive HTTP requests (from browsers), route them to the correct Python function, run that function, and return an HTTP response. Flask is often called a "micro-framework" because it gives you the essentials without forcing you to use a specific database, authentication system, or template engine.

**Why Flask instead of Django or FastAPI?**
- **vs. Django:** Django is a "batteries included" framework with its own ORM, admin panel, and migration system. It's powerful but opinionated and heavier. Flask is simpler — you choose each piece yourself, which gives more flexibility for a project like QUOKKA that uses custom storage (SQLite via raw SQL), custom auth, and streaming responses.
- **vs. FastAPI:** FastAPI is modern and built around async Python, which is excellent for high-concurrency apps. However, streaming SSE responses with FAISS + embedding models in FastAPI requires more careful async handling. Flask's sync model is simpler for CPU-bound tasks (embedding generation).

**What does Flask do in this project specifically?**
- Receives all HTTP requests from browsers and routes them to the right Python function
- Manages sessions (the encrypted cookie that keeps users logged in)
- Renders HTML templates using Jinja2 (built into Flask)
- Provides the `Blueprint` system to organize routes into separate files
- Handles file uploads via `request.files`
- Streams SSE responses via `Response(stream_with_context(...))`

**Which files use Flask?**  
`app.py`, `routes/auth.py`, `routes/chat.py`, `routes/sessions.py`, `routes/upload.py`

---

### Groq API

**What is an API?**  
An API (Application Programming Interface) is a way for two computer programs to talk to each other. In this context, it means QUOKKA sends a request (an HTTP POST with the prompt) to Groq's servers, and Groq's servers send back the AI's response. QUOKKA doesn't run the AI itself — it pays Groq to run it and returns the result.

**What is Groq?**  
Groq (not to be confused with "Grok" by xAI) is a company that built specialized AI inference hardware called LPUs (Language Processing Units) that run large language models extremely fast — often 10–20x faster than standard GPUs. They offer a free API tier. The base URL used in QUOKKA is: `https://api.groq.com/openai/v1/chat/completions`.

**What is LLaMA 3.1 8B and LLaMA 3.3 70B?**  
LLaMA is a family of open-source large language models created by Meta (Facebook's parent company). The numbers mean:
- **8B / 70B**: Billion **parameters**. A parameter is a single number inside the neural network that was tuned during training. More parameters = more "knowledge" stored = better answers, but slower and more memory.
- **3.1 / 3.3**: Version numbers of the LLaMA 3 series.
- **"instant" / "versatile"**: Groq's naming — "instant" = optimized for speed, "versatile" = optimized for quality.

**What are parameters in an LLM?**  
Imagine the AI's "brain" as a massive network of connections, each with a numerical weight. When training, these weights are adjusted billions of times until the network can predict the next word well. 8 billion parameters = 8 billion such weights. With 70 billion, the network can capture more nuanced patterns in language. An 8B model fits in about 5–8 GB RAM; a 70B model needs 40+ GB.

**How did we connect to Groq API?**  
In `models/model_router.py`:
```python
response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY', '')}",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 512,
        "stream": True
    },
    stream=True,
    timeout=30
)
```
The `Authorization: Bearer gsk_...` header is how Groq authenticates us. Without the correct API key, Groq returns a 401 error.

**What does the response look like?**  
When streaming, Groq sends lines like:
```
data: {"id":"...","choices":[{"delta":{"content":"Hello"},"index":0}]}
data: {"id":"...","choices":[{"delta":{"content":" world"},"index":0}]}
data: [DONE]
```
Each line delivers a small piece of the response. `choices[0].delta.content` is the actual text token.

**What is streaming and why do we use it?**  
Streaming means the server sends data as it becomes available, rather than waiting for everything to be ready. Without streaming, users would stare at a blank box for 5–30 seconds waiting for the entire response. With streaming, they see text appearing almost immediately, word by word — dramatically improving the perceived speed and user experience. In HTTP terms, streaming is implemented using chunked transfer encoding and kept-alive connections.

**Where in the code does this happen?**  
In `models/model_router.py`, the `ask_llm_stream()` function (lines 16–53). It is called from `routes/chat.py` at line 108.

---

### FAISS

**What is FAISS?**  
FAISS (Facebook AI Similarity Search) is an open-source library from Meta Research for efficient similarity search in high-dimensional vector spaces. Think of it as a super-fast search engine that, instead of matching keywords, matches mathematical vectors.

**What is a vector?**  
A vector is a list of numbers. For example, `[0.12, -0.45, 0.88, 0.03, ...]`. In this project, each text chunk is converted into a 384-number vector where similar texts produce numerically similar vectors.

**What is vector search?**  
Given a query vector (e.g., "what are the side effects of aspirin?"), vector search finds the stored vectors that are most numerically similar — and those correspond to the most semantically similar text chunks. This is fundamentally different from keyword search (which looks for exact word matches) — vector search understands meaning.

**Why do we need it for document search?**  
When you ask "what causes headaches?", a keyword search would only find chunks containing the exact word "headaches". Vector search would also find chunks about "migraines", "pain relief", and "neurological symptoms" because they are semantically related. This is critical for making document Q&A genuinely useful.

**How does it work in this project?**  
1. User uploads a PDF.
2. Text is extracted and split into ~400-word chunks.
3. Each chunk is converted to a 384-dimensional vector by the embedding model.
4. Vectors are added to a FAISS `IndexFlatL2` index (an exact search index using L2/Euclidean distance).
5. When a user asks a question, the question is also converted to a vector.
6. FAISS finds the 5 closest stored vectors (smallest L2 distance).
7. The corresponding text chunks are retrieved and used in the prompt.

**Which files use it?**  
`memory/document_store.py` (document RAG), `memory/faiss_store.py` (session memory, not active).

---

### Sentence Transformers (BAAI/bge-small-en-v1.5)

**What is an embedding model?**  
An embedding model is a neural network that takes text as input and outputs a fixed-size list of numbers (a vector/embedding) that encodes the semantic meaning of the text. Two sentences with similar meaning will have vectors that are close together in the numerical space.

**What does BAAI/bge-small-en-v1.5 do?**  
"BAAI" = Beijing Academy of Artificial Intelligence. "bge" = BAAI General Embedding. "small" = it is the smallest (and fastest) version. "en" = English. "v1.5" = version 1.5.

It takes any text string and outputs a 384-dimensional vector. It was specifically trained for retrieval tasks — meaning it produces vectors that work well for finding relevant documents. It produces vectors where texts with similar meaning cluster together.

**Why this model specifically?**  
- **Small footprint**: Only ~130 MB to download, runs on CPU without issues.
- **Optimized for retrieval**: Outperforms general-purpose models like `all-MiniLM-L6-v2` on retrieval benchmarks.
- **Fast enough for production**: Can embed 100 chunks in a few seconds on CPU.

**Where is it used in the code?**  
In `models/embedding_manager.py` — loaded as a singleton on first use. Called by `memory/document_store.py` in `get_model()`, `process_file()`, and `retrieve_context()`.

---

### RAG (Retrieval-Augmented Generation)

**What is RAG? Explain from scratch.**  
RAG is a technique that improves AI answers by giving the AI relevant information from a real source before asking it to generate a response. Without RAG, the AI only uses its training data (knowledge frozen at its training cutoff). With RAG, the AI can use up-to-date or specific private documents.

Think of RAG like this: instead of asking a student to answer from memory, you give them the textbook chapter and say "read this, then answer the question." The answer is grounded in the provided text, not just the student's general knowledge.

**Why do we need RAG?**  
- LLMs have a training cutoff — they don't know things that happened after they were trained.
- LLMs don't have access to your private PDFs, company documents, or research papers.
- RAG grounds the AI's answers in specific, verifiable sources rather than general knowledge.
- It reduces "hallucinations" (the AI making things up) because it has real text to reference.

**How does RAG work in QUOKKA step by step?**

1. **Indexing time (when you upload a file):**
   - Text is extracted from PDF/DOCX/TXT
   - Text is split into ~400-word chunks with sentence-aware boundaries
   - Each chunk is embedded into a 384-dimensional vector
   - All vectors are stored in a FAISS index on disk

2. **Query time (when you send a message):**
   - Your question is embedded into a vector
   - FAISS searches for the top 5 most similar chunks
   - Each result's similarity is computed: `cosine_sim = 1 - (L2_distance / 2)`
   - Chunks below 55% similarity are filtered out
   - Remaining chunks are joined and injected into the prompt:
     ```
     Use the provided context when relevant...
     Context:
     [chunk 1 text]
     [chunk 2 text]
     ...
     ```
   - The full prompt (system + context + history + question) is sent to Groq
   - After the response streams, a metadata event is sent with source filenames and the average confidence score

**What happens when you upload a PDF?**  
See the [Simple Explanation section](#what-happens-when-a-user-uploads-a-pdf) above. In code: `routes/upload.py` validates the file, then calls `memory/document_store.py`'s `process_file()`, which chains: `extract_text()` → `chunk_text()` → `get_model().encode()` → `index.add()` → `save()`.

**How does the AI use the PDF content?**  
The AI doesn't see the PDF directly. It receives the relevant text chunks inserted into the prompt string. From the AI's perspective, it's just more text in the message. The instructions say "Use the provided context when relevant."

---

### SQLite

**What is SQLite?**  
SQLite is a relational database engine built into Python's standard library. Unlike PostgreSQL or MySQL (which run as separate server processes you connect to over a network), SQLite stores the entire database in a single file on disk (`data/chats.db`). It's perfect for small to medium applications.

**What tables exist in the database?**  
Three tables: `chats`, `messages`, and `users`. (See [Section 6 — Database Schema](#6-database-schema) for full details.)

**Why SQLite and not PostgreSQL or MySQL?**
- **Zero configuration**: No database server to install, configure, or manage.
- **Works on Render's free tier**: PostgreSQL on Render requires a paid plan; SQLite is just a file.
- **Sufficient for small user bases**: SQLite handles thousands of concurrent users fine for a chat app.
- **Downside**: Cannot be shared across multiple server processes/instances (but with `workers=1` in Gunicorn, this is not an issue).

---

### Flask-Mail

**What is Flask-Mail?**  
Flask-Mail is a Flask extension for sending emails. It integrates with SMTP servers (Simple Mail Transfer Protocol — the standard for email sending). 

**Important note for QUOKKA:** Although `flask-mail` is listed in `requirements.txt`, **the actual email sending code in `services/mail_service.py` does NOT use Flask-Mail**. It uses the **Brevo HTTP API** directly via the `requests` library. The `.env` file still has Gmail SMTP settings (`MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`) from an earlier version of the code, but these are not used. The reason for the switch was that Gmail SMTP is blocked on some cloud hosting providers (including Render's free tier), while Brevo's HTTPS API works everywhere.

**What is Gmail SMTP?**  
SMTP is the protocol email servers use to send messages. Gmail operates an SMTP server at `smtp.gmail.com:587`. You can connect to it from Python and send emails as if they came from your Gmail address.

**What is an App Password and why is it needed?**  
Google no longer allows using your regular Gmail password to authenticate SMTP connections. Instead, you must generate an "App Password" — a 16-character random password specifically for apps. It is required because Google's 2-Step Verification blocks regular password logins for programmatic access.

**What emails does QUOKKA send?**
1. **OTP verification email** — sent during registration and on resend OTP requests
2. **Password reset email** — sent when user requests a forgotten password reset
3. **Welcome email** — sent once after successful email verification

---

### Werkzeug

**What is Werkzeug?**  
Werkzeug is the underlying WSGI toolkit that Flask is built on. It handles HTTP request/response objects, URL routing, and many utilities. In QUOKKA, it is used specifically for **password hashing**.

**How is it used for password security?**  
Two functions are imported from `werkzeug.security`:
```python
from werkzeug.security import check_password_hash, generate_password_hash
```
- `generate_password_hash(password)` — takes a plain-text password and returns a long scrambled string like `scrypt:32768:8:1$abc123$abc...` (the hash).
- `check_password_hash(stored_hash, provided_password)` — returns True if the provided password matches the stored hash.

**What is password hashing and why is it important?**  
Hashing is a one-way mathematical operation. Given "mypassword123", the hash is always the same (e.g., `scrypt:32768:8:1$...`). But given only the hash, you cannot reverse it to get "mypassword123".

This is critical because: **databases get hacked**. If passwords were stored as plain text and a hacker dumped your database, they would immediately have everyone's passwords. With proper hashing (using scrypt, bcrypt, or PBKDF2), even if the database is stolen, the passwords cannot be recovered in any reasonable amount of time.

---

### FPDF2

**What is FPDF2?**  
FPDF2 is a Python library for generating PDF files programmatically. It creates PDF documents by placing text, images, and shapes at specific positions on a page.

**How is PDF export implemented?**  
In `routes/sessions.py`, the `export_chat()` function:
```python
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt=safe_text(f"Chat: {title}"), ln=1, align="C")
for m in messages:
    pdf.set_font("Arial", 'B', 11)        # Bold for role
    pdf.cell(200, 10, txt=f"{m['role'].upper()}:", ln=1)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 10, txt=m['content'])  # Wraps long text
```
A `safe_text()` function converts Unicode characters to Latin-1 (replacing unknowns with `?`) because the Arial font in FPDF2 doesn't support all Unicode characters. The output is written to a `BytesIO` buffer and returned as a file download.

---

### Gunicorn

**What is Gunicorn?**  
Gunicorn (Green Unicorn) is a production-grade Python WSGI (Web Server Gateway Interface) HTTP server. It acts as the bridge between the raw HTTP connections from the internet and your Flask application.

**Why can't we use Flask's built-in server in production?**  
Flask's development server (`app.run()`) is single-threaded, not optimized for performance, not hardened against security issues, and Werkzeug itself warns you "Do not use the development server in a production environment." It is designed for debugging during development, not for handling real users.

**How does Gunicorn help?**  
Gunicorn manages worker processes, handles connection queueing, enforces timeouts, and can be configured to handle concurrent requests. With `workers=1` in `gunicorn.conf.py`, it runs one worker process (appropriate for the low RAM budget of a free Render instance that must also run the embedding model).

Start command on Render: `gunicorn app:app --config gunicorn.conf.py`  
This means: start Gunicorn, load the `app` object from `app.py`, using the config from `gunicorn.conf.py`.

---

## 5. All Dependencies Explained

| Package | Purpose | Used In | If Removed |
|---------|---------|---------|------------|
| `flask` | Web framework — handles HTTP routing, sessions, templates | `app.py`, all routes | App cannot start |
| `flask-mail` | Email extension for Flask (listed but not actively used — Brevo API is used instead) | `requirements.txt` only | No functional impact (currently unused) |
| `flask-cors` | Adds CORS headers to allow cross-origin requests | Available but not explicitly configured in code | No functional impact if same-origin only |
| `gunicorn` | Production WSGI server | `render.yaml` start command | Cannot start in production (only dev server) |
| `python-dotenv` | Loads `.env` file into `os.environ` | `app.py` (line 5: `load_dotenv()`) | All env variables must be set manually in the shell |
| `werkzeug` | Password hashing, file security utilities | `routes/auth.py` (`check_password_hash`, `generate_password_hash`), `routes/upload.py` (`secure_filename`) | Passwords cannot be hashed; filenames not sanitized |
| `requests` | HTTP client for making API calls | `models/model_router.py` (Groq API), `services/mail_service.py` (Brevo API) | Cannot call Groq API or send emails |
| `sentence-transformers` | Loads and runs sentence embedding models | `models/embedding_manager.py` | RAG (document search) completely broken |
| `faiss-cpu` | Vector similarity search library | `memory/document_store.py`, `memory/faiss_store.py` | RAG cannot index or search documents |
| `numpy` | Numerical arrays for FAISS operations | `memory/document_store.py`, `memory/faiss_store.py` | FAISS vectors cannot be created or manipulated |
| `pypdf` | Reads text from PDF files | `memory/document_store.py` (extract_text), `routes/upload.py` (page count check) | PDF uploads fail |
| `python-docx` | Reads text from DOCX files | `memory/document_store.py` (extract_text) | DOCX uploads fail |
| `fpdf2` | Generates PDF files for chat export | `routes/sessions.py` (export_chat) | PDF export fails (TXT export still works) |
| `torch` | Deep learning framework (required by sentence-transformers) | Indirect — `sentence-transformers` depends on it | sentence-transformers fails to load |
| `accelerate` | Optimizes model loading (required by some transformers) | Indirect dependency | Model loading may be slower or fail |

---

## 6. Database Schema

The database file is `data/chats.db`. It contains three tables.

---

### Table: `users`

Stores one row per registered user account.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | Unique user ID, auto-incremented |
| `name` | TEXT NOT NULL | Display name (e.g., "Alice Smith") |
| `email` | TEXT UNIQUE NOT NULL | Email address, stored lowercase. Must be unique. |
| `password_hash` | TEXT NOT NULL | Werkzeug scrypt hash of the password. Never the plain-text password. |
| `is_verified` | INTEGER DEFAULT 0 | 0 = unverified (OTP not yet entered), 1 = verified |
| `otp` | TEXT | The 6-digit OTP code currently active (NULL after verification) |
| `otp_expiry` | TEXT | ISO datetime string when the OTP expires (10 min after generation) |
| `otp_attempts` | INTEGER DEFAULT 0 | Number of wrong OTP attempts. Account deleted at 5. |
| `reset_token` | TEXT | URL-safe random token for password reset (NULL when not in reset flow) |
| `reset_token_expiry` | TEXT | ISO datetime string when the reset token expires (15 min) |
| `created_at` | TEXT | ISO datetime string when the account was created |

---

### Table: `chats`

Stores one row per chat session.

| Column | Type | Description |
|--------|------|-------------|
| `chat_id` | TEXT PRIMARY KEY | UUID string (e.g., `"a534b925-ee0c-..."`) — serves as the unique identifier |
| `title` | TEXT | Chat name shown in sidebar. Auto-set to first 30 chars of first message. |
| `is_private` | INTEGER DEFAULT 0 | 0 = normal chat, 1 = private. Currently always 0 — private chats are never persisted. |
| `created_at` | TEXT | ISO datetime string when the chat was created |
| `is_pinned` | INTEGER DEFAULT 0 | 0 = not pinned, 1 = pinned to top of sidebar |
| `summary` | TEXT | Optional chat summary (not currently generated by the UI, available for future use) |
| `user_id` | INTEGER | Foreign key to `users.id`. Added via ALTER TABLE migration. |

---

### Table: `messages`

Stores one row per message in any chat.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | Auto-incremented row ID, used for ordering |
| `chat_id` | TEXT | Foreign key to `chats.chat_id`. CASCADE DELETE: deleting a chat deletes its messages. |
| `role` | TEXT | Either `"user"` or `"assistant"` |
| `content` | TEXT | The full text of the message |
| `timestamp` | TEXT | ISO datetime string when the message was saved |

---

### Relationships

```
users (1) ──── (many) chats
chats (1) ──── (many) messages
```

A user can have many chats. Each chat has many messages. Messages belong to exactly one chat. Deleting a chat (via `ON DELETE CASCADE`) automatically deletes all its messages.

---

## 7. API Endpoints — Complete Reference

All API endpoints return JSON. All endpoints except auth endpoints require a valid session (set by `login_required`). All 401 responses include `{"error": "Unauthorized", "redirect": "/login"}`.

---

### Authentication Endpoints

---

**`POST /api/auth/register`**  
**Purpose:** Create a new user account and send OTP.  
**Request body:** `{ "name": "Alice", "email": "alice@example.com", "password": "secret123" }`  
**Internal steps:**
1. Validates name (≥2 chars), email (regex), password (≥8 chars, contains digit)
2. Checks if email already exists and is verified → reject with error
3. If email exists unverified → refreshes OTP, resends
4. If new: hashes password, creates user row, generates OTP, sends OTP email in background thread
5. Returns success message

**Success response:** `{ "success": true, "message": "OTP sent to your email." }`  
**Handled by:** `routes/auth.py` — `register()`

---

**`POST /api/auth/verify-otp`**  
**Purpose:** Verify the 6-digit OTP and activate the account.  
**Request body:** `{ "email": "alice@example.com", "otp": "482931" }`  
**Internal steps:**
1. Looks up user by email
2. Checks attempt count (≥5 → delete account, error)
3. Checks OTP expiry (expired → error, no attempt penalty)
4. Checks OTP value (wrong → increment attempts, error with remaining count)
5. Correct OTP: marks user verified, creates Flask session, sends welcome email in background
6. Returns success

**Success response:** `{ "success": true, "message": "Email verified — welcome!" }`  
**Handled by:** `routes/auth.py` — `verify_otp()`

---

**`POST /api/auth/resend-otp`**  
**Purpose:** Generate a new OTP and send it (resets attempt counter).  
**Request body:** `{ "email": "alice@example.com" }`  
**Success response:** `{ "success": true, "message": "New OTP sent." }`  
**Handled by:** `routes/auth.py` — `resend_otp()`

---

**`POST /api/auth/login`**  
**Purpose:** Authenticate an existing verified user.  
**Request body:** `{ "email": "alice@example.com", "password": "secret123" }`  
**Internal steps:**
1. Looks up user by email
2. Checks `check_password_hash(stored_hash, provided_password)`
3. If unverified → returns 401 with `error: "not_verified"` code
4. If wrong password → returns 401 with generic "Invalid email or password" (doesn't reveal if email exists)
5. Creates Flask session: `session["user_id"]`, `session["user_email"]`, `session["user_name"]`

**Success response:** `{ "success": true, "user": {"id": 1, "name": "Alice", "email": "alice@example.com"} }`  
**Handled by:** `routes/auth.py` — `login()`

---

**`POST /api/auth/logout`**  
**Purpose:** Clear the session and log out.  
**Request body:** (none)  
**Success response:** `{ "success": true }`  
**Handled by:** `routes/auth.py` — `logout()`

---

**`POST /api/auth/forgot-password`**  
**Purpose:** Request a password reset email.  
**Request body:** `{ "email": "alice@example.com" }`  
**Internal steps:**
1. Always returns success (prevents email enumeration)
2. If email is valid and account exists and is verified: generates `secrets.token_urlsafe(32)`, stores it with 15-min expiry, sends reset email with link `{BASE_URL}/reset-password?token=...`

**Success response:** `{ "success": true, "message": "If that email is registered, a reset link has been sent." }`  
**Handled by:** `routes/auth.py` — `forgot_password()`

---

**`POST /api/auth/reset-password`**  
**Purpose:** Set a new password using the reset token from email.  
**Request body:** `{ "token": "abc123...", "password": "newpassword1" }`  
**Internal steps:**
1. Looks up user by reset token
2. Checks token expiry (15 minutes)
3. Validates new password (≥8 chars, contains digit)
4. Updates password hash, clears reset token

**Success response:** `{ "success": true, "message": "Password reset successfully." }`  
**Handled by:** `routes/auth.py` — `reset_password()`

---

**`GET /api/auth/me`**  
**Purpose:** Check if the current session is valid; returns user info.  
**Request body:** (none)  
**Success response:** `{ "success": true, "user": {"id": 1, "name": "Alice", "email": "..."} }`  
**401 response:** `{ "error": "Unauthorized" }`  
**Handled by:** `routes/auth.py` — `me()`

---

**`GET /api/auth/profile`** *(requires login)*  
**Purpose:** Get full profile information for the profile page.  
**Success response:** `{ "success": true, "name": "Alice", "email": "...", "created_at": "...", "chat_count": 12, "is_verified": true }`  
**Handled by:** `routes/auth.py` — `get_profile()`

---

**`PUT /api/auth/profile`** *(requires login)*  
**Purpose:** Update the user's display name.  
**Request body:** `{ "name": "Alice B." }`  
**Handled by:** `routes/auth.py` — `update_profile()`

---

**`PUT /api/auth/change-password`** *(requires login)*  
**Purpose:** Change password from the profile page (requires knowing current password).  
**Request body:** `{ "current_password": "old1234", "new_password": "new5678" }`  
**Handled by:** `routes/auth.py` — `change_password()`

---

**`DELETE /api/auth/account`** *(requires login)*  
**Purpose:** Permanently delete account and all associated chats/messages.  
**Internal steps:** Deletes all messages for user's chats, deletes user's chats, deletes user row, clears session.  
**Handled by:** `routes/auth.py` — `delete_account()`

---

### Chat Endpoints

---

**`POST /api/chat`** *(requires login)*  
**Purpose:** Send a message and receive a streaming AI response.  
**Request body:**
```json
{
  "message": "What are black holes?",
  "model": "llama3.1:8b",
  "session_id": "uuid-of-chat",
  "is_private": false,
  "temperature": 0.7,
  "memory_enabled": true
}
```
**Response:** `text/event-stream` (SSE). Multiple events:
- `data: {"text": "Black"}` — token by token
- `data: {"metadata": {"sources": ["research.pdf"], "confidence": 82.5}}` — after response, if RAG was used
- `data: {"title": "What are black holes?..."}` — after response, if chat was auto-titled  
**Handled by:** `routes/chat.py` — `api_chat()`

---

**`GET /api/chats`** *(requires login)*  
**Purpose:** Get all non-private chats for the sidebar.  
**Response:** `{ "chats": [{"chat_id": "...", "title": "...", "is_pinned": false, ...}, ...] }`  
**Handled by:** `routes/sessions.py` — `get_normal_chats()`

---

**`POST /api/chat/new`** *(requires login)*  
**Purpose:** Create a new empty chat session.  
**Request body:** `{ "title": "New Chat" }` (optional)  
**Response:** `{ "chat_id": "uuid", "title": "New Chat" }`  
**Handled by:** `routes/sessions.py` — `create_chat()`

---

**`GET /api/chat/<chat_id>`** *(requires login)*  
**Purpose:** Load a specific chat with full message history.  
**Response:** `{ "chat": {"chat_id": "...", "title": "...", "messages": [{"role": "user", "content": "..."}, ...]} }`  
**Handled by:** `routes/sessions.py` — `get_chat()`

---

**`PUT /api/chat/<chat_id>`** *(requires login)*  
**Purpose:** Rename a chat.  
**Request body:** `{ "title": "My Chat about Black Holes" }`  
**Handled by:** `routes/sessions.py` — `rename_chat()`

---

**`DELETE /api/chat/<chat_id>`** *(requires login)*  
**Purpose:** Delete a chat and its FAISS session data.  
**Handled by:** `routes/sessions.py` — `delete_chat()`

---

**`PUT /api/chat/<chat_id>/pin`** *(requires login)*  
**Purpose:** Toggle pin/unpin a chat.  
**Response:** `{ "success": true, "is_pinned": true }`  
**Handled by:** `routes/sessions.py` — `toggle_pin()`

---

**`GET /api/chats/search`** *(requires login)*  
**Purpose:** Search all chats by title or message content.  
**Query param:** `?q=black+holes`  
**Response:** `{ "results": [{chat objects}] }`  
**Handled by:** `routes/sessions.py` — `search_chats()`

---

**`GET /api/chat/<chat_id>/export`** *(requires login)*  
**Purpose:** Download chat as TXT or PDF.  
**Query param:** `?format=txt` or `?format=pdf`  
**Response:** File download (`text/plain` or `application/pdf`)  
**Handled by:** `routes/sessions.py` — `export_chat()`

---

**`POST /api/upload`** *(requires login)*  
**Purpose:** Upload a document (PDF/DOCX/TXT) for RAG indexing.  
**Request body:** `multipart/form-data` with a `file` field  
**Response:** `{ "success": true, "message": "file.pdf uploaded and indexed successfully", "filename": "file.pdf", "size_mb": 1.2 }`  
**Handled by:** `routes/upload.py` — `upload_file()`

---

## 8. Authentication System — Full Explanation

### How registration works step by step

1. User fills in name, email, password, confirm password on `/signup`
2. JavaScript validates passwords match, then calls `POST /api/auth/register`
3. Server validates: name ≥ 2 chars, valid email regex, password ≥ 8 chars with digit
4. Server checks database: if email exists and is verified → "account already exists"
5. If email exists unverified → refreshes OTP, resends (allows retry without re-registering)
6. New user: `generate_password_hash(password)` creates the hash, `create_user()` inserts to DB
7. `_new_otp()` = `str(secrets.randbelow(900000) + 100000)` creates a 6-digit number
8. OTP stored with `datetime.now() + timedelta(minutes=10)` expiry
9. `_send_async(send_otp_email, ...)` starts a daemon thread to send email without blocking
10. Page transitions to OTP input panel

### What is OTP and why we use it

OTP = One-Time Password. It is a code that can only be used once and expires after a short time. We use it to verify that the user actually controls the email address they provided. Without OTP verification, anyone could create accounts with fake emails or other people's emails.

### How OTP is generated and stored

```python
def _new_otp():
    return str(secrets.randbelow(900000) + 100000)   # 6-digit
```

`secrets.randbelow(900000)` generates a cryptographically secure random number from 0 to 899999. Adding 100000 ensures it is always 6 digits (100000 to 999999). `secrets` is used instead of `random` because `random` is predictable — it uses a seeded pseudo-random generator. `secrets` uses the operating system's entropy source.

The OTP and its expiry datetime are stored in the `users` table columns `otp` and `otp_expiry`.

### How email verification works

When the user submits the OTP:
1. Server looks up user by email
2. Checks `otp_attempts` — if ≥ 5, deletes the account and returns error
3. Checks `otp_expiry` — if expired, returns error (no attempt penalty, as expiry is outside the user's control)
4. Checks if submitted OTP matches stored OTP
5. Wrong: increments `otp_attempts`, returns error with remaining attempts count
6. Correct: calls `verify_user_email()` which sets `is_verified=1`, clears OTP fields, and resets attempts
7. Sets Flask session keys: `user_id`, `user_email`, `user_name`
8. Sends welcome email in background thread

### How login works

1. User submits email + password to `POST /api/auth/login`
2. Server fetches user by email from DB
3. `check_password_hash(stored_hash, provided_password)` — if wrong, returns generic "Invalid email or password" (doesn't reveal if email exists, preventing enumeration)
4. If user exists but `is_verified=0` → returns 401 with `error: "not_verified"` code (JS shows "Verify my email instead" button)
5. If verified and password matches → creates session, returns user object

### What is a session and how Flask sessions work

A session is a way to remember who a user is across multiple requests. HTTP is stateless — each request is independent with no memory of previous requests. Sessions solve this.

Flask's session uses a **signed cookie**. When you log in:
1. Flask stores data in `session["user_id"] = 1` etc.
2. This data is serialized, signed with `SECRET_KEY` using HMAC, and stored in a cookie sent to the browser
3. On every subsequent request, the browser sends back this cookie
4. Flask verifies the HMAC signature (proving the cookie wasn't tampered with), then reads the data
5. The data in `session` is then available to all route handlers

In QUOKKA, the session is also backed by `sessions.db` for persistence across server restarts.

### How password hashing works

Werkzeug's `generate_password_hash()` uses **scrypt** by default — a memory-hard key derivation function. It:
1. Generates a random salt (adds uniqueness so two identical passwords produce different hashes)
2. Runs many iterations of a computationally expensive hash function
3. Returns a string containing the algorithm name, parameters, salt, and hash: `scrypt:32768:8:1$salt$hash`

This means: even if the database is compromised, cracking the passwords would take billions of computer-years.

### How forgot password flow works

1. User enters email on `/forgot-password`, calls `POST /api/auth/forgot-password`
2. Server **always returns success** (even if email doesn't exist) — prevents attackers from finding out which emails are registered
3. Internally: if email is valid, verified, and exists → generates `secrets.token_urlsafe(32)` (a 43-character URL-safe random string like `abc123XYZ...`)
4. Stores token + expiry (15 minutes) in user row
5. Sends email with link: `{BASE_URL}/reset-password?token=abc123XYZ...`

### How reset token is generated and validated

`secrets.token_urlsafe(32)` creates 32 bytes of random data encoded as URL-safe base64 (letters, digits, `-`, `_`). It is statistically impossible to guess (2^256 possibilities).

On the reset page:
1. JavaScript reads `?token=...` from the URL
2. User enters new password
3. `POST /api/auth/reset-password` with token + new password
4. Server: `get_user_by_reset_token(token)` — SELECT WHERE reset_token = ?
5. Checks expiry — if expired, error
6. Updates `password_hash`, clears `reset_token` and `reset_token_expiry`

### What `login_required` decorator does

```python
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized", "redirect": "/login"}), 401
        return f(*args, **kwargs)
    return decorated
```

When `@login_required` is placed above a route function, Python replaces the function with `decorated`. Before the real route logic runs, it checks the Flask session for `user_id`. If absent, returns 401 immediately. The browser's `window.fetch` override in `app.js` intercepts all 401 responses and redirects to `/login`.

### Security considerations

- Passwords are hashed with scrypt — cannot be reversed
- OTP is cryptographically random — cannot be predicted
- Reset tokens are cryptographically random — cannot be guessed
- Generic error messages on login — doesn't reveal which emails are registered
- OTP attempt limiting — prevents brute-force of the 6-digit code (only 10^6 = 1M possibilities)
- OTP expiry — 10 minutes limits the attack window
- Reset token expiry — 15 minutes

---

## 9. Chat System — Full Explanation

### What happens when user sends a message

1. User types in the `<textarea id="chat-input">` and presses Enter or clicks the send button
2. `sendMessage(text)` is called in `app.js`
3. Checks: not already streaming, not empty
4. Adds user message to the UI immediately (using `textContent` to prevent XSS)
5. Creates `AbortController` for stream cancellation
6. Sets `isStreaming = true`, disables input and button
7. Creates a "bot" message div with "Thinking..." indicator
8. Sends `POST /api/chat` with: message, model, session_id, is_private, temperature, memory_enabled
9. Server builds prompt (see below) and opens a streaming connection to Groq
10. Tokens stream back; browser reads them from the `ReadableStream`
11. When complete: renders markdown, shows action buttons (Copy, Regenerate)
12. Re-enables input, sets `isStreaming = false`

### What is SSE (Server Sent Events)?

SSE is a web standard where a server keeps an HTTP connection open and sends data to the browser over time, formatted as:
```
data: {"text": "Hello"}\n\n
data: {"text": " world"}\n\n
data: [DONE]\n\n
```

Each event is text prefixed with `data: ` and terminated by two newlines (`\n\n`). The browser's Fetch API can read this in chunks via a `ReadableStream`. It is simpler than WebSockets (one-directional, no handshake) and works through most HTTP proxies.

In QUOKKA, Flask returns the response with `mimetype="text/event-stream"` and uses `stream_with_context(generate())` where `generate()` is a Python generator that yields SSE strings.

### How streaming works technically

**Server side** (`routes/chat.py`):
```python
def generate():
    full_response = ""
    for chunk in ask_llm_stream(prompt, model, temperature):
        yield chunk  # Each chunk is: "data: {...}\n\n"
        if chunk.startswith("data: "):
            payload = json.loads(chunk[6:])
            if "text" in payload:
                full_response += payload["text"]
    # After all tokens, save to DB
    if not is_private and session_id:
        storage.append_message(session_id, "user", message)
        storage.append_message(session_id, "assistant", full_response)
```

**Client side** (`static/js/app.js`):
```javascript
const reader = response.body.getReader();
const decoder = new TextDecoder("utf-8");
let buffer = "";

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop();  // Keep incomplete last chunk
    for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = JSON.parse(line.slice(6));
        if (data.text) {
            fullText += data.text;
            textContent.textContent = fullText;  // Live update
        }
    }
}
// After complete: render markdown
textContent.innerHTML = renderMarkdown(fullText);
```

During streaming: `textContent.textContent` (plain text, fast). After complete: `textContent.innerHTML` with rendered Markdown. This two-phase approach avoids the performance cost of re-rendering Markdown on every token.

### How chat history is saved

Messages are saved **after** the full response is received (inside `generate()` in `routes/chat.py`):
```python
if not is_private and session_id:
    storage.append_message(session_id, "user", message)
    storage.append_message(session_id, "assistant", full_response)
```
Both messages are inserted into the `messages` table with `role` and `content` and the current timestamp.

### What is private mode and how it works

Private mode is a client-side only mode:
- **Server side:** `is_private=True` in the request tells the server not to save messages and not to run RAG
- **Client side:** Messages are stored in a JavaScript array `privateMessages = []` in browser memory only
- When the tab is closed, all private messages are gone — they were never written to the server database
- The sidebar is visually blurred (CSS `pointer-events: none; opacity: 0.3; filter: blur(4px)`) to reinforce that no chats are being saved
- A red warning banner confirms "Private Mode Active (Messages are not saved)"

### How memory context works (last 6 messages)

When `memory_enabled=true` and not private and a `session_id` exists:
```python
chat = storage.get_chat(session_id)
messages = chat.get("messages", [])[-6:]  # Last 6 messages
for m in messages:
    chat_context_lines.append(f"{m['role'].capitalize()}: {m['content']}")
chat_context = "\n".join(chat_context_lines)
```
The last 6 messages (3 pairs of user+assistant) are formatted as:
```
User: What is a black hole?
Assistant: A black hole is...
User: How do they form?
```
This context is prepended to the prompt so the AI can refer back to the conversation.

### How the prompt is constructed

```python
prompt = f"""You are QUOKKA, a helpful AI assistant. Answer clearly, concisely, and avoid any filler sentences.
{doc_context_text}
{chat_context}

Question:
{message}

Answer:"""
```

Where `doc_context_text` (if RAG found relevant chunks) is:
```
\nUse the provided context when relevant. If the context is insufficient, answer using general knowledge 
while clearly distinguishing document-derived information from model knowledge.\n\nContext:\n[chunks]\n
```

---

## 10. RAG Pipeline — Full Explanation

### What file formats are supported

- **PDF** (`.pdf`) — up to 50 pages, up to 15 MB
- **DOCX** (`.docx`) — Microsoft Word format, no page limit beyond file size
- **TXT** (`.txt`) — plain text, no page limit beyond file size

### How text is extracted from each format

From `memory/document_store.py`'s `extract_text()`:
```python
if ext == ".txt":
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
elif ext == ".pdf":
    reader = PdfReader(file_path)
    pages = reader.pages[:50]  # First 50 pages max
    for page in pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
elif ext == ".docx":
    doc = Document(file_path)
    for para in doc.paragraphs:
        text += para.text + "\n"
```

### What is chunking and why we do it

Chunking = splitting a large text into smaller overlapping pieces. This is needed because:
1. **Embedding models have input limits** — most can only handle ~512 tokens at once.
2. **Precision** — embedding an entire 50-page document into one vector loses all detail. Smaller chunks let FAISS find the specific relevant paragraph, not just "the document is vaguely related."
3. **Context window** — the AI model has a limit on how much text it can process. We can't send the entire document; we send only the relevant parts.

QUOKKA uses paragraph-aware chunking: `re.split(r'\n\s*\n', text)` splits on blank lines (paragraph boundaries). Paragraphs are accumulated into chunks of ~400 words. When a paragraph alone exceeds 400 words, it is split at sentence boundaries.

### How embeddings are generated

```python
vectors = self.get_model().encode(
    file_chunks,
    batch_size=16,              # Process 16 chunks at a time to avoid RAM spike
    normalize_embeddings=True   # L2-normalize so cosine similarity = dot product
)
vectors = np.array(vectors).astype("float32")  # FAISS requires float32
```

`encode()` runs each chunk through the `BAAI/bge-small-en-v1.5` neural network and returns a 384-dimensional float array for each chunk. With 100 chunks, this produces a 100×384 matrix.

### How FAISS index is built

```python
self.index = faiss.IndexFlatL2(self.dimension)  # 384-dimensional exact search
# ...
self.index.add(vectors)  # Add all vectors at once
```

`IndexFlatL2` is an exact search index using L2 (Euclidean) distance — it compares every query vector against every stored vector. For small document collections (hundreds of chunks), this is perfectly fast. For large-scale deployments (millions of vectors), approximate search indexes would be better.

### How similarity search works

At query time:
```python
vec = self.get_model().encode([query], normalize_embeddings=True)
vec = np.array(vec).astype("float32")
k = min(top_k, self.index.ntotal)  # Can't request more than we have
distances, indices = self.index.search(vec, k)
```

`index.search(vec, k)` returns the `k` closest vectors and their L2 distances. Since vectors are L2-normalized, L2 distance and cosine similarity are related: `cosine_sim = 1 - (L2_distance / 2)`.

### What is the similarity threshold

In `routes/chat.py`:
```python
cos_sim = 1 - (r["score"] / 2)
if cos_sim > 0.55:  # Similarity threshold
    filtered_results.append(r)
```

Only chunks with cosine similarity above 55% are included. This prevents the AI from receiving irrelevant context when the user's question has nothing to do with the uploaded document.

### How retrieved context is injected into prompt

All passing chunks are joined and inserted into the prompt:
```python
doc_context = "\n\n".join(context_parts)
doc_context_text = f"\nUse the provided context when relevant...\n\nContext:\n{doc_context}\n"
```

### What is confidence score and how it's calculated

```python
avg_distance /= len(filtered_results)   # Average L2 distance
cosine_sim = 1 - (avg_distance / 2)     # Convert to cosine similarity
confidence_pct = max(0, round(cosine_sim * 100, 1))  # As percentage
```

The confidence score (e.g., 82.5%) represents how closely the retrieved chunks matched the user's question semantically. It is displayed below the AI response in the metadata block alongside the source filenames.

---

## 11. Frontend Explanation

### How the UI is structured (no framework, vanilla JS)

QUOKKA uses no JavaScript framework (no React, Vue, or Angular). The entire frontend is:
- **HTML** (`templates/`) — structure and semantic markup
- **CSS** (`static/css/`) — all styling, animations, and layout
- **Vanilla JavaScript** (`static/js/`) — all behavior and API calls

This was a deliberate choice for simplicity — no build step, no node_modules, no webpack. The HTML is rendered server-side by Flask/Jinja2. JavaScript manipulates the DOM dynamically after page load.

### What app.js does

`app.js` (619 lines) is the complete frontend logic for the chat page:
- Initializes by grabbing all DOM element references
- Sets up event listeners for: chat input (Enter key), send button, new chat button, privacy toggle, file upload, settings modal, export buttons, search input, logout button
- Manages state: `currentSessionId`, `isStreaming`, `lastUserMessage`, `activeStreamController`, `privateMessages`
- Fetches session list from API and renders it dynamically
- Sends messages and reads streaming SSE responses
- Handles all real-time UI updates during streaming
- Overrides `window.fetch` globally to redirect to `/login` on any 401 response

### How SSE streaming is handled in JS

The browser reads the response as a `ReadableStream`. The key insight is that network chunks don't align with SSE event boundaries — a single chunk may contain part of an event, one event, or multiple events. The code handles this with a buffer:
```javascript
buffer += decoder.decode(value, { stream: true });
const lines = buffer.split("\n\n");
buffer = lines.pop();  // The last element might be incomplete
for (const line of lines) {
    // process complete events
}
```
`lines.pop()` removes and saves the last element (which may be an incomplete event waiting for more data). Complete events are processed; the incomplete fragment is kept in `buffer` for the next iteration.

### How markdown rendering works (marked.js)

`marked.js` is loaded from a CDN before `app.js`. It converts Markdown text to HTML:
```javascript
function renderMarkdown(text) {
    if (typeof marked !== "undefined") {
        return marked.parse(text);
    }
    // Fallback: escape HTML
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;")...
}
```
During streaming: `textContent.textContent = fullText` (raw text, fast, no HTML parsing).  
After streaming completes: `textContent.innerHTML = renderMarkdown(fullText)` (HTML, supports headings, code blocks, bold, etc.).

This two-phase approach is a performance optimization — parsing Markdown on every token would be expensive and cause visible flickering.

### How the model dropdown works

In `templates/index.html`:
```html
<select id="model-select" class="dropdown">
  <option value="llama3.1:8b">LLaMA 3.1 8B ⚡ Fast</option>
  <option value="llama3.1:70b">LLaMA 3.3 70B 🔥 Smart</option>
</select>
```

In `app.js`, when sending a message: `model: modelSelect.value`. The server receives `"llama3.1:8b"` or `"llama3.1:70b"`, looks it up in `GROQ_MODEL_MAP`, and sends the actual Groq model ID.

### How private mode toggle works

```javascript
privacyCheckbox.addEventListener("change", (e) => {
    updatePrivacyMode(e.target.checked);
});

function updatePrivacyMode(isPrivate) {
    if (isPrivate) {
        document.body.classList.add("privacy-mode");  // CSS blurs sidebar
        privateWarning.style.display = "flex";
        privateMessages = [];
        startNewChat();  // Shows "You are in Private Mode" message
    } else {
        document.body.classList.remove("privacy-mode");
        privateWarning.style.display = "none";
        privateMessages = [];
        startNewChat();  // Returns to normal mode
    }
}
```

The `privacy-mode` CSS class applies:
```css
body.privacy-mode .sidebar {
    pointer-events: none;
    opacity: 0.3;
    filter: blur(4px);
}
```

### How file upload works

```javascript
fileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    fileNameSpan.textContent = "Uploading...";
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (data.success) {
        fileNameSpan.textContent = file.name + " (Indexed ✓)";
    }
});
```

`FormData` is the browser's built-in class for building multipart form data (the format used for file uploads). It automatically sets the correct `Content-Type: multipart/form-data; boundary=...` header.

### How export works

```javascript
exportTxtBtn.addEventListener("click", () => {
    if (!currentSessionId || privacyCheckbox.checked) return;
    window.open(`/api/chat/${currentSessionId}/export?format=txt`, "_blank");
});
```

`window.open()` opens the download URL in a new browser tab. Since the server responds with `Content-Disposition: attachment`, the browser automatically downloads the file instead of displaying it.

### What auth.js does

`auth.js` is a shared utility library (not a page handler). It provides:
- HTTP helpers: `postJson()`, `putJson()` — send JSON and handle errors
- UI helpers: `showError()`, `showSuccess()`, `clearAlert()` — manage alert box display
- Password toggle: `togglePw()` — eye icon to show/hide password
- Password strength: `strengthScore()`, `updateStrength()` — animated strength bar
- OTP wiring: `setupOTP()` — auto-focus, backspace, paste support for 6-box OTP input
- OTP reading: `getOTP()` — collects all 6 values
- Countdown: `startCountdown()` — "Resend in 59s..." timer
- Loading state: `setLoading()` — disable button + show spinner

It is included via `<script src="/static/js/auth.js">` in all auth pages and provides functions that the inline page scripts call.

---

## 12. Security Features

| Security Measure | How It Works | Where It's Implemented |
|---|---|---|
| **Password hashing** | Passwords stored as scrypt hashes — cannot be reversed | `routes/auth.py` using `werkzeug.security.generate_password_hash` |
| **OTP expiry (10 minutes)** | OTP stored with ISO timestamp; checked against `datetime.now()` before validating | `routes/auth.py` — `verify_otp()` |
| **OTP attempt limiting (5 max)** | Attempt counter incremented on wrong guess; account deleted at 5 | `routes/auth.py` — `verify_otp()`, `memory/chat_storage.py` — `increment_otp_attempts()` |
| **Session-based authentication** | Flask sessions use HMAC-signed cookies — cannot be forged without `SECRET_KEY` | `app.py` + all routes using `session[]` |
| **`login_required` protection** | Decorator prevents unauthenticated access to all API endpoints | `routes/auth_middleware.py` — applied in `routes/chat.py`, `routes/sessions.py`, `routes/upload.py` |
| **Private mode (zero server storage)** | `is_private=True` prevents any DB writes; client-side only history | `routes/chat.py` checks `is_private` before every `storage.append_message()` |
| **Email verification before login** | `is_verified` must be 1 to log in; OTP verification sets it | `routes/auth.py` — `login()` checks `is_verified` |
| **Reset token expiry (15 minutes)** | Token stored with expiry timestamp; checked in `reset_password()` | `routes/auth.py` — `reset_password()` |
| **XSS prevention (textContent)** | User-provided text set via `textContent` not `innerHTML`, preventing HTML injection | `static/js/app.js` — all user messages use `textContent` |
| **Filename sanitization** | `secure_filename()` removes path traversal characters from uploaded filenames | `routes/upload.py` using `werkzeug.utils.secure_filename` |
| **File size validation** | 15 MB limit set at Flask level + double-checked after save | `app.py` (`MAX_CONTENT_LENGTH`), `routes/upload.py` |
| **PDF page limit** | Rejects PDFs > 50 pages to prevent memory exhaustion | `routes/upload.py`, `memory/document_store.py` |
| **Email enumeration prevention** | Forgot password always returns success regardless of whether email exists | `routes/auth.py` — `forgot_password()` |
| **Generic login errors** | "Invalid email or password" instead of "Email not found" | `routes/auth.py` — `login()` |
| **`debug=False` in production** | Flask debug mode disabled in production (debug mode can expose source code) | `app.py` line 114: `app.run(..., debug=False)` |
| **Global 401 redirect** | All 401 API responses redirect to `/login` | `static/js/app.js` — `window.fetch` override |

---

## 13. Environment Variables

All environment variables are stored in the `.env` file. The app uses `python-dotenv` (`load_dotenv()` in `app.py`) to load them into `os.environ` at startup.

| Variable | What It Controls | What Happens If Missing | Example Value |
|---|---|---|---|
| `SECRET_KEY` | Flask session signing key. Used to sign the session cookie so it cannot be forged. | Sessions cannot be trusted; Flask falls back to a weak default `"quokka-dev-secret-change-me"` | `xK9#mP2$qRvL8nWz` (any random string, ≥32 chars recommended) |
| `GROQ_API_KEY` | Authentication for Groq API. Sent in every `Authorization: Bearer ...` header to Groq. | All AI responses fail with 401 from Groq | `gsk_abc123...` (from console.groq.com) |
| `MAIL_SERVER` | Gmail SMTP server hostname (legacy, not currently used by the Brevo-based code) | Not actively used | `smtp.gmail.com` |
| `MAIL_PORT` | Gmail SMTP port (legacy, not currently used) | Not actively used | `587` |
| `MAIL_USERNAME` | Gmail address (legacy, not currently used) | Not actively used | `you@gmail.com` |
| `MAIL_PASSWORD` | Gmail App Password (legacy, not currently used) | Not actively used | `abcd efgh ijkl mnop` |
| `BASE_URL` | Base URL of the deployed app. Used to build the password reset link: `{BASE_URL}/reset-password?token=...` | Reset links point to `http://localhost:8000` even in production | `https://quokka-ai.onrender.com` |
| `FLASK_ENV` | Sets Flask environment (`development` or `production`) | Flask defaults to production | `development` |
| `PORT` | Port for the development server. Render sets its own `PORT` automatically. | Flask defaults to 8000 | `8000` |
| `ENABLE_RAG` | If `"true"`, the warmup function pre-loads the embedding model at startup. | Defaults to `false` — embedding model loaded lazily on first upload | `true` or `false` |
| `BREVO_API_KEY` | Authentication for Brevo email API (required for email to work in production) | All email sending raises `RuntimeError` — OTP, reset, welcome emails all fail | `xkeysib-...` (from Brevo dashboard) |
| `MAIL_FROM` | Sender email address used in Brevo API calls (must be verified in Brevo) | Email sending raises `RuntimeError` | `noreply@quokka.ai` |

> **Note:** `BREVO_API_KEY` and `MAIL_FROM` are not in the current `.env` file but are required by `services/mail_service.py`. The `.env` file shows Gmail SMTP credentials from an older version — these need to be updated for production deployment.

---

## 14. Deployment Plan

### Why Render was chosen

Render is a cloud hosting platform that offers:
- **Free tier** for small web services (with some limitations: sleeps after inactivity, ephemeral storage)
- **Simple deployment**: connects to GitHub, auto-deploys on every push to `main`
- **Python-native**: auto-detects Python apps, runs pip install automatically
- **Environment variable management**: secrets stored separately from code in the Render dashboard

### What changes are needed for production

1. **Email service**: Switch from legacy Gmail SMTP config to Brevo. Add `BREVO_API_KEY` and `MAIL_FROM` to Render environment.
2. **`BASE_URL`**: Set to the actual Render URL (e.g., `https://quokka-ai.onrender.com`)
3. **`SECRET_KEY`**: Generate a strong random key (e.g., `python -c "import secrets; print(secrets.token_hex(32))"`)
4. **Database persistence**: Render free tier has ephemeral storage — the SQLite database and FAISS files are lost on every redeploy. For production: either upgrade to a Render plan with a persistent disk, or migrate to PostgreSQL.

### What environment variables need to be set on Render

In Render dashboard → Service → Environment:
```
SECRET_KEY          = <32+ char random string>
GROQ_API_KEY        = gsk_...
BREVO_API_KEY       = xkeysib-...
MAIL_FROM           = your-verified-sender@domain.com
BASE_URL            = https://your-service-name.onrender.com
ENABLE_RAG          = true
```

### What is Gunicorn and how to configure it

Gunicorn is configured via `gunicorn.conf.py` with:
- `workers = 1` — one process (FAISS index is process-local; more workers would each have separate indexes)
- `worker_class = "sync"` — synchronous I/O (correct for SSE streaming)
- `timeout = 120` — 120 second timeout per request (AI generation can take 30+ seconds)

Start command: `gunicorn app:app --config gunicorn.conf.py`

### How to push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/QUOKKA.git
git push -u origin main
```
Ensure `.gitignore` is properly set so `.env`, `data/`, `uploads/`, `memory/faiss_data/`, `sessions.db` are NOT pushed.

### Step-by-step deployment instructions

1. **Create a Brevo account** at brevo.com and get an API key. Verify a sender email address.
2. **Create a GitHub repository** and push your code (without `.env`).
3. **Create a Render account** at render.com.
4. In Render: **New → Web Service → Connect your GitHub repo**.
5. Configuration:
   - Name: `quokka-ai`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --config gunicorn.conf.py`
6. In **Environment**: add all required environment variables listed above.
7. Click **Deploy**. Render installs dependencies and starts the app.
8. Visit the Render URL to confirm the login page loads.
9. **Test the email**: visit `https://your-url.onrender.com/test-email` to verify Brevo is working.
10. Every future push to `main` on GitHub triggers an automatic redeploy.

---

## 15. Known Limitations & Future Improvements

### Current Limitations

| Limitation | Details |
|---|---|
| **SQLite won't scale** | SQLite has write locking — only one write at a time. For >100 concurrent users, PostgreSQL is necessary. |
| **Free Render tier sleeps** | After 15 minutes of inactivity, the free Render service "sleeps." The next request takes 30–60 seconds to wake up. |
| **No rate limiting** | There are no limits on how many API calls a single user or IP can make. A malicious user could exhaust the Groq API quota. |
| **Mobile UI partially complete** | The sidebar hides below 768px, but there's no hamburger menu to access chat history on mobile. |
| **FAISS index lost on redeploy** | Render's free tier has no persistent disk. Every redeploy erases `data/` and `memory/doc_data/` — all uploaded documents and the SQLite database are lost. |
| **All documents shared** | The document RAG index is global — all users' uploaded documents are in the same FAISS index. User A's document affects User B's responses. |
| **No real-time collaboration** | Only one user session per server process; no WebSocket-based real-time features. |
| **`ENABLE_RAG` env var** | The warmup uses an env var but the code defaults the embedding model name to `all-MiniLM-L6-v2` in `document_store.py` while `app.py` warmup uses the same name — but `document_store.py` actually uses `BAAI/bge-small-en-v1.5`. This inconsistency means the warmup might load a different model than what document_store.py uses. |
| **`flask-mail` and Brevo** | `flask-mail` is in `requirements.txt` but unused. The `.env` has Gmail SMTP settings that are not used. This creates confusion about the actual email mechanism. |

### Future Improvements to Consider

| Improvement | Why |
|---|---|
| **Switch to PostgreSQL** | Scales to thousands of concurrent users; persistent on Render with a paid disk |
| **Add rate limiting (Flask-Limiter)** | Prevent API abuse and Groq quota exhaustion |
| **Persistent volume on Render** | Attach a disk to keep SQLite and FAISS data across redeploys |
| **Multi-user document isolation** | Each user's uploaded documents should be in their own FAISS namespace |
| **Per-session semantic memory** | Activate `memory/faiss_store.py` to give the AI better long-term memory |
| **PWA support** | Add a service worker and manifest to make the app installable as a desktop/mobile app |
| **Chat sharing feature** | Generate a public link to share a conversation |
| **Mobile sidebar** | Add a hamburger menu for mobile access to chat history |
| **Streaming title generation** | Generate smarter chat titles using a separate LLM call |
| **Activate Pinecone store** | Implement `memory/pinecone_store.py` for cloud-scale vector search |
| **Remove flask-mail / clean .env** | Remove the unused dependency and align `.env` with the actual Brevo-based email code |
| **Chunk overlap** | The current `chunk_text()` accepts an `overlap` parameter but doesn't implement it — add overlapping chunks for better retrieval at chunk boundaries |

---

## 16. Glossary

**API (Application Programming Interface)**  
A way for two software programs to communicate with each other. Like a waiter in a restaurant — you (the app) tell the waiter (the API) what you want, the kitchen (the other program) prepares it, and the waiter brings it back. In QUOKKA, we use the Groq API to "order" AI responses.

**LLM (Large Language Model)**  
A type of artificial intelligence trained on vast amounts of text that can understand and generate human language. Examples: GPT-4, Claude, LLaMA. LLMs predict the next word given everything before it — do this billions of times and you get coherent responses.

**Parameters (in context of AI models)**  
The numerical "weights" inside a neural network that are tuned during training. More parameters = more capacity to learn and remember patterns. LLaMA 3.1 8B has 8 billion parameters. Think of them as the neurons in the AI's brain.

**Token**  
The basic unit that LLMs work with. A token is roughly a word or part of a word. "Hello" = 1 token. "Unbelievable" might be 2 tokens. LLMs generate one token at a time, which is why you see text appearing word by word during streaming.

**Streaming**  
Sending data incrementally as it becomes available, instead of waiting for everything to be ready. In QUOKKA, instead of waiting for the full AI response (which takes seconds), we show each word as it's generated — making the interface feel much faster.

**RAG (Retrieval-Augmented Generation)**  
A technique where the AI's response is grounded in specific retrieved documents. Instead of generating purely from its training memory, the AI first searches a database of relevant text chunks, then uses those chunks plus its training knowledge to answer. Like giving an open-book exam instead of a closed-book one.

**Vector**  
A list of numbers that represents something in mathematical space. In QUOKKA, each text chunk is converted into a 384-number vector by the embedding model. Vectors that are numerically close to each other represent text that is semantically similar.

**Embedding**  
The process of converting text (or any data) into a vector. The embedding model (BAAI/bge-small-en-v1.5) takes a string like "What causes headaches?" and outputs 384 numbers that capture its meaning. Similar sentences produce similar embedding vectors.

**FAISS (Facebook AI Similarity Search)**  
A library that efficiently finds the most similar vectors in a large collection. In QUOKKA, it stores document chunk vectors and quickly finds which chunks are most similar to the user's question vector.

**OTP (One-Time Password)**  
A code that can only be used once and expires after a short period. Used in QUOKKA to verify that a new user owns the email address they provided during registration. QUOKKA generates a 6-digit OTP (e.g., 482931) that expires after 10 minutes.

**Session**  
A way to remember a user's identity across multiple web requests. When you log into QUOKKA, the server creates a session that includes your user ID. Your browser stores a session cookie. On every future request, the browser sends the cookie back so the server knows who you are — without you re-entering your password every time.

**Hashing**  
A mathematical one-way function that converts any input into a fixed-size scrambled string. "password123" → `scrypt:32768:8:1$salt$longhash`. Cannot be reversed. QUOKKA stores password hashes (not the passwords themselves) so even if the database is stolen, attackers cannot get the real passwords.

**SMTP (Simple Mail Transfer Protocol)**  
The standard internet protocol for sending email. QUOKKA originally used Gmail's SMTP server but switched to the Brevo HTTP API because SMTP port 587 is often blocked by cloud hosting providers.

**SSE (Server-Sent Events)**  
A web standard for servers to push data to browsers over a single, long-lived HTTP connection. Data arrives as lines formatted `data: {...}\n\n`. In QUOKKA, each AI token is sent as an SSE event: `data: {"text": "Hello"}\n\n`. Simpler than WebSockets for one-directional server→client streaming.

**Blueprint (Flask)**  
A Flask feature for organizing route handlers into separate modules. In QUOKKA, auth routes, chat routes, session routes, and upload routes are each in separate Blueprint objects (`auth_bp`, `chat_bp`, `sessions_bp`, `upload_bp`) that are registered with the main `app` in `app.py`. This keeps the code organized instead of having all routes in one giant file.

**WSGI (Web Server Gateway Interface)**  
A Python standard (PEP 3333) that defines how web servers (like Gunicorn) talk to Python web applications (like Flask). Think of it as a universal plug: any WSGI-compatible server can run any WSGI-compatible Python app. QUOKKA's `app.py` creates a WSGI-compatible Flask application (`app = Flask(__name__)`).

**Gunicorn**  
A production-grade Python WSGI HTTP server. Flask's built-in development server is not suitable for production (single-threaded, not hardened). Gunicorn manages multiple worker processes, handles connection queuing, enforces timeouts, and is battle-tested for production deployments. QUOKKA uses it with 1 worker, sync class, and 120-second timeout.

---

*End of QUOKKA Project Documentation Report*

---

> **Report generated by:** Complete code analysis of all 30+ project files  
> **Lines of code covered:** ~4,000+ lines across Python, JavaScript, HTML, and CSS  
> **Completeness:** Every file, every endpoint, every technology, every security measure documented
