# QUOKKA AI Assistant — Complete Project Documentation Report

> **Version:** 1.0 | **Prepared after reading every file in the project.**  
> This document is written so that a teammate, a first-time reviewer, or a non-technical reader
> can understand every part of this codebase from scratch.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [How the App Works — Simple Explanation](#2-how-the-app-works--simple-explanation)
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

QUOKKA is a **self-hosted AI chat assistant** — a web application where users can log in, have conversations with powerful AI language models, upload documents, and get AI answers grounded in their own files.

Think of it like a private version of ChatGPT that you run yourself, where you control the data, the models, and the experience.

### What problem does it solve?

Most AI chat tools are either:
- **Closed and expensive** (ChatGPT, Claude) — you pay per message and your data goes to a third-party server.
- **Technically complex to self-host** — open-source models require expensive GPUs.

QUOKKA solves this by using **Groq's free API** to run large language models at zero cost and near-zero latency, while keeping everything else (user accounts, chat history, document search) under your own control on your own server.

### Who is it built for?

- Developers who want a customizable AI assistant
- Students and researchers who want to chat with their own documents (papers, notes, textbooks)
- Small teams who want a shared internal AI tool
- Anyone who values privacy and wants full control over their AI conversations

### What can a user do with it?

1. **Register** with their email and verify their identity via a 6-digit OTP code
2. **Chat** with AI models in real-time, watching the response appear word by word
3. **Upload documents** (PDF, Word, TXT) and ask questions about them
4. **Switch AI models** — choose between speed-optimized or quality-optimized models
5. **Organize conversations** — search, pin, rename, and delete chats
6. **Export conversations** as downloadable TXT or PDF files
7. **Use private mode** — chat without anything being saved to the server
8. **Manage their account** — update name, change password, delete account

### What makes it different from a regular chatbot?

| Feature | Regular Chatbot | QUOKKA |
|---------|----------------|--------|
| Document Q&A | ❌ | ✅ RAG with FAISS vector search |
| Streaming responses | Sometimes | ✅ Always — token by token |
| Email auth with OTP | ❌ | ✅ Full OTP verification |
| Private mode | ❌ | ✅ Zero server storage |
| Export to PDF | ❌ | ✅ |
| Self-hostable | ❌ | ✅ |
| Multiple models | Sometimes | ✅ 4 models available |

---

## 2. How the App Works — Simple Explanation

### The Main User Journey

**Step 1: User opens the browser**  
The user navigates to the app URL (e.g., `http://localhost:8000`). Flask's `app.py` checks whether the user is logged in. If not, it redirects them to `/login`.

**Step 2: User signs up with email**  
The user fills in their name, email, and password on the `/signup` page. The frontend (`signup.html`) sends a `POST` request to `/api/auth/register`. The server validates the input, hashes the password, creates a database record, and generates a random 6-digit number (the OTP).

**Step 3: User gets OTP on email**  
The server calls `mail_service.py`, which uses Flask-Mail to send a beautifully formatted HTML email containing the 6-digit code. The email is sent via Gmail's SMTP server. The OTP is stored in the database and expires in 10 minutes.

**Step 4: User verifies and logs in**  
The user enters the 6-digit code into the OTP input boxes on the page. The frontend sends the code to `/api/auth/verify-otp`. The server checks if the code matches and hasn't expired. If correct, it marks the account as verified, creates a Flask session (a server-side cookie that proves the user is logged in), and redirects them to the main chat page. A welcome email is sent automatically.

**Step 5: User types a question**  
On the main chat page (`index.html`), the user types a message in the text area at the bottom. When they press Enter or click the send button, the JavaScript in `app.js` captures the text.

**Step 6: App sends it to Groq API**  
The JavaScript sends an HTTP POST request to `/api/chat` with the user's message, selected model, session ID, and settings (temperature, memory toggle). The Flask route in `routes/chat.py` receives this. It:
1. Checks if any documents have been uploaded and performs a similarity search (RAG)
2. Loads the last 6 messages of the current conversation for context
3. Builds a structured prompt combining the context, document results, and user question
4. Makes an HTTP request to Groq's API with streaming enabled

**Step 7: AI generates response**  
Groq's servers run the selected LLM (e.g., LLaMA 3.1 8B) and begin generating the response one "token" (roughly one word or word-piece) at a time. They send each token back to QUOKKA's server as it's generated.

**Step 8: Response streams back word by word**  
Groq sends the tokens using a format called Server-Sent Events (SSE). QUOKKA's server passes each token directly to the browser without waiting for the full response. The JavaScript in `app.js` reads each incoming token using the browser's `ReadableStream` API and appends it to the chat bubble in real time.

**Step 9: User sees the answer**  
The user watches the AI's answer appear word by word, just like watching someone type. When the response is complete, the JavaScript renders the text as Markdown (so code blocks, bold text, and lists look properly formatted). The complete conversation is saved to the SQLite database.

---

### What happens when a user uploads a PDF?

1. The user clicks the paperclip icon in the chat input.
2. They select a `.pdf`, `.docx`, or `.txt` file. The browser sends it via `FormData` to `/api/upload`.
3. `routes/upload.py` saves the file to the `uploads/` folder.
4. The first 2,500 characters are extracted and sent to the Groq API, which generates a **document summary**, a list of **topics**, and **suggested questions** to ask about it. These are shown to the user instantly.
5. In a **background thread**, the complete document is processed: text is extracted, split into chunks (~400 words each), each chunk is converted into a numerical vector by the `BAAI/bge-small-en-v1.5` embedding model, and all vectors are stored in a FAISS index on disk.
6. From this point on, every chat message triggers a vector search against this index. If relevant passages are found, they are injected into the prompt automatically.

---

### What happens when private mode is on?

1. The user toggles the "Private Chat" switch in the header.
2. The `private-warning` banner appears: "Private Mode Active (Messages are not saved)."
3. All chat messages are kept only in the JavaScript variable `privateMessages` in the browser's memory — nothing is sent to the server for storage.
4. The `session_id` is not sent with chat requests, so the server never attempts to save the conversation.
5. When the user closes the tab or refreshes, all private messages are gone permanently.

---

### What happens when user exports a chat?

1. The user clicks the TXT or PDF button in the top header.
2. The JavaScript opens a new browser tab pointing to `/api/chat/{id}/export?format=txt` (or `pdf`).
3. `routes/sessions.py` fetches the full chat from the database.
4. For **TXT**: The chat is formatted as plain text and returned as a downloadable file.
5. For **PDF**: The `fpdf2` library creates a PDF document with each message formatted with role labels, and it is returned as a downloadable file.

---

## 3. Complete Folder Structure

```
QUOKKA/
├── app.py
├── requirements.txt
├── README.md
├── PROJECT_REPORT.md
├── .env
├── .gitignore
├── sessions.db                  ← legacy SQLite file (not used; active DB is in data/)
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
│   └── pinecone_store.py
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
├── data/                        ← auto-created; holds chats.db (SQLite)
├── uploads/                     ← auto-created; holds uploaded documents
├── memory/doc_data/             ← auto-created; holds FAISS document index
└── memory/faiss_data/           ← auto-created; holds per-session FAISS indexes
```

---

### File-by-File Breakdown

---

#### `app.py`

**What it is:** The main entry point and application factory for the entire Flask web application.

**What it does:**
- Creates the Flask application object
- Configures Flask-Mail with Gmail SMTP settings from environment variables
- Registers the four route Blueprints: `chat_bp`, `sessions_bp`, `upload_bp`, `auth_bp`
- Defines page routes (`/`, `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/profile`) that serve HTML templates
- Runs a **background warmup thread** on startup: if documents exist, it pre-loads the embedding model into RAM so the first chat request doesn't lag
- Starts the Flask development server when run directly

**Talks to:** `routes/chat.py`, `routes/sessions.py`, `routes/upload.py`, `routes/auth.py`, `memory/document_store.py`, `models/embedding_manager.py`

**Why needed:** Without this file, the server doesn't exist. It's the spine that connects every other component.

```python
# Example: the warmup thread that loads models before the first request
def warmup():
    import time
    time.sleep(1)
    if doc_store.has_documents():
        get_embedding_model("BAAI/bge-small-en-v1.5")
```

---

#### `routes/auth.py`

**What it is:** The complete authentication system — handles everything related to user identity.

**What it does:** Defines 9 API endpoints:
- `POST /api/auth/register` — validate input, hash password, create user, send OTP email
- `POST /api/auth/verify-otp` — check OTP validity, mark account verified, start session
- `POST /api/auth/resend-otp` — generate new OTP and resend
- `POST /api/auth/login` — verify credentials, create session
- `POST /api/auth/logout` — clear session
- `POST /api/auth/forgot-password` — generate reset token, send reset email
- `POST /api/auth/reset-password` — validate token, update password hash
- `GET /api/auth/me` — return current user info (used by frontend on load)
- `GET /api/auth/profile` — return full profile + chat count
- `PUT /api/auth/profile` — update display name
- `PUT /api/auth/change-password` — verify current password, update to new hash
- `DELETE /api/auth/account` — delete all user data

**Talks to:** `memory/chat_storage.py` (for all DB operations), `services/mail_service.py` (to send emails), `routes/auth_middleware.py` (for `@login_required`)

**Why needed:** Provides complete user account management with email-verified identity.

---

#### `routes/auth_middleware.py`

**What it is:** A single-function utility file providing a route protection decorator.

**What it does:** Defines `login_required` — a Python decorator that wraps any route function. Before the route executes, it checks whether `user_id` is present in the Flask session. If not, it immediately returns a 401 Unauthorized JSON response with a redirect hint.

**Talks to:** Used by `routes/auth.py` on profile-related endpoints.

**Why needed:** Without this, profile and account management routes would be accessible without being logged in.

```python
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized", "redirect": "/login"}), 401
        return f(*args, **kwargs)
    return decorated
```

---

#### `routes/chat.py`

**What it is:** The most important backend file — the endpoint that powers every conversation.

**What it does:** Handles `POST /api/chat`. When a message arrives:
1. Validates message length (max 4,000 characters)
2. Forces `memory_enabled = False` if private mode is on
3. If documents exist and mode is not private, runs FAISS similarity search via `document_store.py`
4. Filters retrieved chunks by similarity threshold (cosine similarity > 0.55)
5. Calculates a confidence percentage for the match quality
6. Loads the last 6 messages from chat history for conversation context
7. Constructs a structured prompt
8. Streams the response from Groq API using a Python generator
9. After streaming, saves the messages to SQLite (unless private)
10. Auto-generates a chat title from the first message if the title is still "New Chat"

**Talks to:** `models/model_router.py`, `memory/document_store.py`, `memory/chat_storage.py`, `routes/auth_middleware.py`

**Why needed:** This file is the engine of the entire product. Remove it and the chat feature stops working completely.

---

#### `routes/sessions.py`

**What it is:** Manages everything related to saving, loading, and organizing chat sessions.

**What it does:** Defines 8 endpoints:
- `GET /api/chats` — return all saved (non-private) chats, ordered by pin status then date
- `POST /api/chat/new` — create a new chat in SQLite, return the new `chat_id`
- `GET /api/chat/<id>` — return a full chat with all its messages
- `PUT /api/chat/<id>` — rename a chat
- `DELETE /api/chat/<id>` — delete chat from SQLite and FAISS
- `PUT /api/chat/<id>/pin` — toggle pin status
- `GET /api/chats/search` — search chat titles and message content
- `GET /api/chat/<id>/export` — export as TXT or PDF using `fpdf2`

**Talks to:** `memory/chat_storage.py`, `memory/faiss_store.py`

**Why needed:** Without this, users can't manage, review, or download their conversations.

---

#### `routes/upload.py`

**What it is:** Handles file upload and triggers document intelligence.

**What it does:**
1. Accepts `POST /api/upload` with a file in `multipart/form-data`
2. Validates file type (only `.pdf`, `.docx`, `.txt` allowed)
3. Saves file to `uploads/` directory using `werkzeug.utils.secure_filename`
4. Extracts the first 2,500 characters and calls `ask_llm_json()` to get a summary, topics, and questions from the AI
5. Spawns a background `threading.Thread` to process the full document into FAISS
6. Returns the AI-generated insights immediately so the user doesn't have to wait for indexing

**Talks to:** `memory/document_store.py`, `models/model_router.py`

**Why needed:** This is the entry point for the entire RAG feature. Without it, document search doesn't exist.

---

#### `memory/chat_storage.py`

**What it is:** The database access layer — every read and write to SQLite goes through this file.

**What it does:**
- Defines all SQLite table creation (chats, messages, users) via `init_storage()` which runs on import
- Handles migration from an old legacy JSON format to SQLite automatically
- Provides pure functions for every database operation: `create_user`, `get_user_by_email`, `verify_user_email`, `set_user_otp`, `create_chat`, `append_message`, `get_chat`, `delete_chat`, `toggle_pin_chat`, `search_chats`, `update_user_name`, `get_user_chat_count`, `delete_user_account`, etc.
- Uses `sqlite3.Row` factory so rows behave like dictionaries
- Enables WAL (Write-Ahead Logging) journal mode for better concurrent access performance

**Talks to:** Nothing — it is the lowest layer. All other modules call it.

**Why needed:** Every piece of persistent user data flows through this file. Remove it and all storage breaks.

---

#### `memory/document_store.py`

**What it is:** The RAG engine — handles document ingestion, chunking, embedding, FAISS indexing, and retrieval.

**What it does:**
- `extract_text(file_path)`: Reads text from `.txt`, `.pdf` (using `pypdf`), or `.docx` (using `python-docx`)
- `chunk_text(text)`: Splits text into ~400-word chunks, paragraph-aware, with sentence-level fallback for very long paragraphs
- `process_file(file_path, filename)`: Orchestrates the full pipeline: extract → chunk → embed → add to FAISS → save to disk
- `retrieve_context(query, top_k=5)`: Converts query to a vector, searches FAISS for nearest neighbors, returns matching text chunks with their L2 distance scores
- `has_documents()`: Quick check (without loading the model) of whether any documents have been indexed
- `save()`: Persists the FAISS index and chunk/source arrays to disk as `.faiss`, `.npy` files

**Talks to:** `models/embedding_manager.py` (for the SentenceTransformer model), `faiss` library

**Why needed:** This is the brain of document search. Without it, uploaded files have no effect on AI answers.

---

#### `memory/faiss_store.py`

**What it is:** A per-session vector memory store — currently **reserved for future use** and not active in the main chat pipeline.

**What it does:** Implements the same FAISS pattern as `document_store.py` but keyed by `session_id`. The idea is to store all messages from a chat session as vectors, enabling semantic search over conversation history ("find what was said about X 20 messages ago") instead of just the recent 6 messages.

The file's own comment says:
> "NOTE: FaissStore is NOT currently wired into the active request pipeline."

The only place it's used currently is in `routes/sessions.py` where `delete_session()` is called when a chat is deleted — to clean up any FAISS files that might exist for that session.

**Talks to:** `models/embedding_manager.py`

**Why needed for now:** Provides clean-up functionality when chats are deleted. Future: will enable long-term semantic memory.

---

#### `memory/pinecone_store.py`

**What it is:** A stub (placeholder) file for a future Pinecone cloud vector database integration.

**What it does:** Contains an empty `PineconeStore` class with `TODO` comments explaining what each method should eventually do. All methods are no-ops that return empty strings. It is **never imported by any active code**.

**Talks to:** Nothing (currently unused)

**Why needed:** Serves as a design document for a future cloud-scale vector memory feature. Can be deleted without affecting anything.

---

#### `models/model_router.py`

**What it is:** The Groq API client — handles all communication with the AI.

**What it does:**
- Defines `GROQ_MODEL_MAP`: a dictionary that maps internal model names (used by the frontend) to Groq's actual model IDs
- `ask_llm_stream(prompt, model, temperature)`: Makes an HTTP POST to Groq's `/openai/v1/chat/completions` with `"stream": True`. Reads the response line by line and yields each SSE chunk as `data: {"text": "..."}` — compatible with the frontend's stream reader
- `ask_llm_json(prompt, model, temperature)`: Same request but with `"stream": False`. Returns the parsed JSON object from the AI's response. Used by `upload.py` to get document insights

```python
GROQ_MODEL_MAP = {
    "llama3.1:8b":      "llama-3.1-8b-instant",
    "llama3.1:70b":     "llama3-70b-8192",
    "mistral:latest":   "mixtral-8x7b-32768",
    "phi:latest":       "gemma2-9b-it",
    "tinyllama:latest": "gemma2-9b-it",
}
```

**Talks to:** Groq's external API over HTTPS using `requests`

**Why needed:** All AI responses come through this file. Remove it and the app is just a chat UI with no AI.

---

#### `models/embedding_manager.py`

**What it is:** A thread-safe singleton manager for the SentenceTransformer embedding model.

**What it does:**
- Uses a class-level lock (`threading.Lock`) to ensure the model is only loaded once, even if multiple threads call `get_model()` at the same time
- Downloads and caches the `BAAI/bge-small-en-v1.5` model from HuggingFace on first call
- Returns the same model instance on all subsequent calls (singleton pattern)

**Talks to:** `sentence_transformers` library

**Why needed:** The embedding model takes several seconds to load. Loading it once and reusing it prevents lag on every document search request.

---

#### `services/__init__.py`

**What it is:** An empty file that marks the `services/` directory as a Python package.

**What it does:** Nothing. Its presence tells Python: "treat this folder as a module."

**Why needed:** Without this file, `from services.mail_service import ...` would fail with an import error.

---

#### `services/mail_service.py`

**What it is:** The email sending module.

**What it does:**
- `_base_wrapper(body_content)`: Creates a consistent dark-themed HTML email template with the QUOKKA branding
- `_send_html(subject, recipients, html_body)`: Gets the Flask-Mail extension from the current app context and sends the email
- `send_otp_email(email, name, otp)`: Sends a verification email with the 6-digit OTP displayed in large yellow text
- `send_reset_email(email, name, reset_link)`: Sends a password reset email with a styled button linking to the reset page
- `send_welcome_email(email, name)`: Sends a welcome confirmation after successful email verification

**Talks to:** Flask-Mail extension (configured in `app.py`), Gmail SMTP server

**Why needed:** Email-based OTP verification and password reset are core security features. Without this, users can't register or recover their accounts.

---

#### `templates/index.html`

**What it is:** The main chat interface — the page users spend most of their time on.

**What it does:**
- Contains the two-column layout: a sidebar (chat list, search, user info) and a main content area (chat messages, input box, header with controls)
- Includes the model selector dropdown with four models
- Has the private chat toggle, TXT/PDF export buttons, and settings gear icon
- Contains the settings modal with temperature slider and memory toggle
- References `marked.min.js` (from CDN) for Markdown rendering and `app.js` for all logic
- Uses Phosphor Icons (from CDN) for the icon system

**Talks to:** Served by `app.py`, logic driven by `static/js/app.js`

---

#### `templates/login.html`

**What it is:** The login page.

**What it does:**
- Presents email and password fields
- Handles the case where the user is unverified: shows a "Resend OTP" button and an OTP entry panel inline (six individual digit boxes)
- Contains inline JavaScript that calls the `postJson`, `showError`, `hideError`, `setupOTPInputs` functions from `auth.js`
- On successful login, redirects to `/`

---

#### `templates/signup.html`

**What it is:** The registration page.

**What it does:**
- Shows name, email, password, and confirm-password fields
- Has a live password strength bar (Weak / Medium / Strong) that updates as the user types
- On successful API call, hides the form and shows the 6-box OTP entry panel
- Has a countdown timer on the Resend OTP button (60 seconds)

---

#### `templates/forgot_password.html`

**What it is:** The "forgot password" page.

**What it does:**
- Simple form with an email input
- Calls `POST /api/auth/forgot-password` — which always responds with success (to prevent email enumeration)
- On success, hides the form and shows "Reset link sent! Check your inbox."

---

#### `templates/reset_password.html`

**What it is:** The page users land on after clicking the reset link in their email.

**What it does:**
- Reads the `?token=...` parameter from the URL
- If no token is present, immediately shows an error
- Shows new password and confirm password fields with a strength bar
- Calls `POST /api/auth/reset-password` with the token and new password
- On success, shows a confirmation message and redirects to login after 2 seconds

---

#### `templates/profile.html`

**What it is:** The user profile management page, the most complex HTML template in the project.

**What it does:**
- Loads the user's profile data from `GET /api/auth/profile` on page load
- **Section 1:** Displays avatar (first letter of name), full name, email, and join date
- **Section 2:** Edit display name form — calls `PUT /api/auth/profile`
- **Section 3:** Change password form with strength bar — calls `PUT /api/auth/change-password`
- **Section 4:** Account stats grid — total chats, member since date, account status (Verified ✓)
- **Section 5:** Danger Zone — "Delete Account" button triggers a confirmation modal; calls `DELETE /api/auth/account` then redirects to login
- Includes all its own CSS inline in a `<style>` block (does not use `auth.css` for most styles)

---

#### `static/js/app.js`

**What it is:** The entire frontend brain for the main chat page. The largest single file in the project (619 lines).

**What it does:** (Detailed explanation in Section 11)

---

#### `static/js/auth.js`

**What it is:** A shared utility library for all auth pages.

**What it does:** (Detailed explanation in Section 11)

---

#### `static/css/styles.css`

**What it is:** The main stylesheet for the chat UI (`index.html` and `profile.html`).

**What it does:** Defines the dark-mode design system — layout (`app-container`, `sidebar`, `main-content`), chat message bubbles, the input box, the settings modal, the sidebar chat list items with pin/rename/delete actions, the private mode warning banner, the metadata block shown when RAG sources are found, and responsive styles.

---

#### `static/css/auth.css`

**What it is:** The stylesheet for all authentication pages (login, signup, forgot password, reset password).

**What it does:** Styles the card-based centered layout, the branded QUOKKA header, input fields, the OTP digit boxes, buttons, the password strength bar, and spinner animations.

---

## 4. Technology Stack — Deep Explanation

### Flask

**What is Flask?**  
Flask is a Python **web framework** — a set of tools that makes it easy to build a web server. It handles incoming HTTP requests (when someone visits a URL or submits a form) and generates responses (HTML pages, JSON data, files).

**Why Flask instead of Django or FastAPI?**
- **Django** is a "batteries-included" framework — it has its own ORM, admin panel, and many built-in features. For a project this size, Django would add unnecessary complexity.
- **FastAPI** is optimized for building pure API backends. QUOKKA also needs to serve HTML pages (templates), where Flask's Jinja2 templating is a better fit.
- **Flask** was chosen because it's lightweight, has a minimal learning curve, and gives full control over every component. Its Blueprint system makes it easy to organize routes into separate files.

**What does Flask do in this project specifically?**
- Routes every URL to the right Python function
- Manages user sessions via encrypted cookies
- Serves HTML templates via Jinja2
- Integrates with Flask-Mail for email sending
- Provides `Response` with `stream_with_context` for SSE streaming

**Which files use Flask:** `app.py`, `routes/auth.py`, `routes/chat.py`, `routes/sessions.py`, `routes/upload.py`, `routes/auth_middleware.py`, `services/mail_service.py`

---

### Groq API

**What is an API?**  
An API (Application Programming Interface) is a way for two programs to talk to each other over the internet. In this case, our server sends an HTTP request to Groq's server saying "generate a response to this prompt," and Groq's server sends back the AI's response.

**What is Groq?**  
Groq is a company that built specialized AI inference hardware (Language Processing Units, or LPUs) that can run large language models **much faster** than regular GPUs. They offer a free API to run popular open-source models like LLaMA. For QUOKKA, this means near-instant AI responses at zero cost.

**What is LLaMA 3.1 8B and LLaMA 3 70B?**  
LLaMA (Large Language Model Meta AI) is a family of AI language models released by Meta (Facebook). The number after it (8B, 70B) refers to the number of **parameters** in the model.

**What are parameters?**  
Imagine the AI model as a giant network of mathematical relationships — billions of knobs and dials. Each knob is a "parameter." When the model was trained, each knob was set to a specific value by learning from trillions of words of text. More parameters generally means a smarter, more nuanced model, but also more computation needed.
- **8B = 8 Billion parameters** — fast, good quality, runs in seconds
- **70B = 70 Billion parameters** — slower, significantly smarter, better reasoning

**How did we connect to Groq API?**  
In `models/model_router.py`, we make a standard HTTPS POST request:

```python
response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GROQ_API_KEY}",  # proves we have access
        "Content-Type": "application/json"           # tells Groq we're sending JSON
    },
    json={
        "model": "llama-3.1-8b-instant",  # which model to use
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,       # creativity level (0=deterministic, 1=creative)
        "max_tokens": 512,        # max length of response
        "stream": True            # send tokens as they're generated, not all at once
    },
    stream=True   # keep the HTTP connection open for streaming
)
```

**What does the response look like?**  
When streaming, Groq sends a continuous stream of lines. Each line looks like:
```
data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}
data: [DONE]
```

We extract the `content` field from each line and forward it to the browser.

**What is streaming and why do we use it?**  
Without streaming, the user would stare at a blank screen for 5–10 seconds while the model generates the full response, then see it all at once. With streaming, tokens appear one by one starting within milliseconds, which feels natural and responsive.

**Where in the code does this happen?**  
`models/model_router.py` — functions `ask_llm_stream()` and `ask_llm_json()`

---

### FAISS

**What is FAISS?**  
FAISS (Facebook AI Similarity Search) is a library built by Meta for **very fast vector similarity search**. Think of it as a special-purpose database optimized for one thing: "find the N most similar items to this one."

**What is a vector?**  
A vector is a list of numbers. For example, `[0.12, -0.45, 0.88, ...]`. In the context of AI, text is converted into vectors where similar meanings produce similar numbers. The sentence "What is machine learning?" and "Explain artificial intelligence" would produce vectors that are mathematically close to each other.

**What is vector search?**  
Traditional text search looks for exact keyword matches. Vector search looks for *conceptual similarity*. "How do I bake bread?" would match a chunk about "kneading dough" even if the word "bake" never appears in that chunk.

**Why do we need it for document search?**  
When a user asks "explain the conclusion of this paper," we need to find the relevant paragraphs from a 50-page PDF. Keyword search would fail if different words were used. Vector search finds the semantically similar chunks regardless of exact wording.

**How does it work in this project?**
1. Each document chunk is converted to a 384-dimensional vector (a list of 384 numbers)
2. All vectors are stored in a FAISS `IndexFlatL2` index (flat L2 = exact search using Euclidean distance)
3. When a query comes in, it's also converted to a 384-dimensional vector
4. FAISS finds the `top_k` stored vectors closest to the query vector in 384-dimensional space
5. The corresponding text chunks are returned as context

**Which files use it:** `memory/document_store.py`, `memory/faiss_store.py`

---

### Sentence Transformers (BAAI/bge-small-en-v1.5)

**What is an embedding model?**  
An embedding model is a neural network that converts text into vectors (lists of numbers). Unlike language models that generate text, embedding models just *understand* text and express that understanding as a point in mathematical space.

**What does BAAI/bge-small-en-v1.5 do?**  
It converts any piece of text into a 384-dimensional vector. BAAI stands for Beijing Academy of Artificial Intelligence, and "bge" stands for "BAAI General Embedding." The `small` variant uses only 33 million parameters — it's fast to run and produces excellent quality embeddings for semantic search.

**Why this model specifically?**
- **384 dimensions** — small enough to store millions of chunks without using too much RAM or disk
- **High quality** — consistently ranks near the top of benchmarks for sentence similarity tasks
- **Fast** — can embed thousands of chunks in seconds on a CPU
- **Open and free** — no API key required, downloaded from HuggingFace on first use

**Where is it used in the code:**  
`models/embedding_manager.py` loads it. `memory/document_store.py` uses it to embed chunks and queries.

---

### RAG (Retrieval Augmented Generation)

**What is RAG?**  
RAG stands for Retrieval Augmented Generation. It is a technique to make an AI answer questions based on specific documents that it wasn't trained on. 

Think of it like an open-book exam. Without RAG, the AI only knows what it learned during training. With RAG, before answering, the AI is given relevant pages from a book to read, then generates its answer based on those pages plus its general knowledge.

**Why do we need RAG?**  
LLMs are trained on general internet data. They don't know about your specific PDF — your research paper, your company's documentation, your personal notes. RAG bridges this gap.

**How does RAG work in QUOKKA step by step?**

*During document upload:*
1. Text is extracted from the file (PDF → text via `pypdf`, DOCX → text via `python-docx`, TXT → read directly)
2. Text is split into overlapping chunks of ~400 words, respecting paragraph boundaries
3. Each chunk is embedded by `BAAI/bge-small-en-v1.5` into a 384-float vector
4. Vectors are added to a FAISS index and saved to disk

*During a chat message:*
1. The user's message is embedded into a 384-float vector
2. FAISS searches for the 5 most similar chunks from all uploaded documents (top_k=5)
3. Each match comes with an L2 distance score (lower = more similar)
4. Chunks are filtered: only those where cosine similarity > 0.55 (55%) are kept
5. A confidence score is calculated: `confidence = (1 - avg_distance/2) * 100`
6. The retained chunks are joined and inserted into the prompt as "Context"
7. The AI uses this context in its answer
8. The frontend displays the source filenames and confidence percentage in a metadata block below the answer

**What happens when you upload a PDF?**  
Covered above — text extraction → chunking → embedding → FAISS indexing.

**How does the AI use the PDF content?**  
The relevant chunks are prepended to the prompt:
```
Use the provided context when relevant. If the context is insufficient, 
answer using general knowledge...

Context:
[chunk 1 text]

[chunk 2 text]

Question:
[user's message]

Answer:
```

---

### SQLite

**What is SQLite?**  
SQLite is a **file-based relational database**. Unlike PostgreSQL or MySQL which run as a separate server process, SQLite is embedded directly into the application — the entire database is a single `.db` file on disk.

**What tables exist in the database?**  
Three tables: `chats`, `messages`, and `users`. (See Section 6 for complete schema.)

**Why SQLite and not PostgreSQL or MySQL?**
- **Zero configuration** — no database server to install, configure, or maintain
- **Perfect for small-to-medium user bases** — handles thousands of concurrent reads well, and WAL mode improves write concurrency
- **Portable** — the entire database is a single file that can be copied, backed up, or moved trivially
- **Free and built into Python** — the `sqlite3` module is in Python's standard library, no extra installation needed

The main trade-off: SQLite does not handle many simultaneous *writes* as gracefully as PostgreSQL. For a small deployment, this is not a problem.

---

### Flask-Mail

**What is Flask-Mail?**  
Flask-Mail is a Flask extension that makes it easy to send emails from a Flask application. It integrates with the Flask app configuration and provides a `Mail` object.

**How does email sending work?**  
QUOKKA uses Gmail as the SMTP (Simple Mail Transfer Protocol) server. When `mail_service.py` calls `mail.send(msg)`, Flask-Mail connects to `smtp.gmail.com` on port 587, authenticates with your Gmail credentials, and sends the email on your behalf.

**What is Gmail SMTP?**  
SMTP is the standard internet protocol for sending email between servers. Gmail provides an SMTP server that anyone with a Gmail account can use to send emails programmatically — up to 500 per day on the free tier.

**What is an App Password and why is it needed?**  
If you have 2-factor authentication (2FA) enabled on your Gmail account (which you should), Gmail won't accept your regular password from a script. An **App Password** is a special 16-character password you generate specifically for one application. It bypasses 2FA for that one app only. You get it from: Google Account → Security → 2-Step Verification → App Passwords.

**What emails does QUOKKA send?**
1. **OTP verification email** — sent on registration with the 6-digit code
2. **Welcome email** — sent after successful email verification
3. **Password reset email** — sent when user requests a reset link

---

### Werkzeug

**What is Werkzeug?**  
Werkzeug is the low-level WSGI toolkit that Flask is built on. In QUOKKA, we use two specific utilities from it:

1. **`werkzeug.security.generate_password_hash`** — takes a plain-text password and returns a secure hash
2. **`werkzeug.security.check_password_hash`** — checks if a plain-text password matches a stored hash
3. **`werkzeug.utils.secure_filename`** — sanitizes uploaded filenames (removes `../`, spaces, and special characters that could be used in path traversal attacks)

**How is it used for password security?**

```python
# When user registers:
password_hash = generate_password_hash("mypassword123")
# Stored in DB: "pbkdf2:sha256:600000$abc123...[long hash]"

# When user logs in:
check_password_hash(stored_hash, "mypassword123")  # → True
check_password_hash(stored_hash, "wrongpassword")  # → False
```

**What is password hashing and why is it important?**  
Hashing is a one-way mathematical transformation. You cannot reverse a hash to get the original password. This means that even if someone steals the database, they get a list of hashes, not passwords. They would need to try billions of guesses to crack each one. Werkzeug uses PBKDF2-HMAC-SHA256 with 600,000 iterations — a deliberately slow algorithm that makes brute-force attacks computationally expensive.

---

### FPDF2

**What is FPDF2?**  
FPDF2 (Free PDF) is a Python library for creating PDF documents from scratch in code.

**How is PDF export implemented?**  
In `routes/sessions.py`, when the export format is `pdf`:
1. A new `FPDF()` object is created
2. A page is added with `pdf.add_page()`
3. The font is set to Arial 12pt
4. The chat title is written as a centered cell
5. For each message, the role (USER/ASSISTANT) is written in bold, then the content in regular weight using `multi_cell()` which handles word wrapping automatically
6. The text is encoded to `latin-1` (FPDF2's default encoding) using `replace` for any characters it can't handle
7. The PDF binary output is written to an in-memory `BytesIO` buffer
8. Flask's `send_file()` returns it as a downloadable attachment

---

### Gunicorn

**What is Gunicorn?**  
Gunicorn (Green Unicorn) is a production-grade Python WSGI HTTP server. It's the standard way to deploy Flask applications in production.

**Why can't we use Flask's built-in server in production?**  
Flask's development server (`app.run()`) is designed for one developer testing locally. It:
- Can only handle one request at a time
- Is not optimized for performance
- Has a warning in its output: "WARNING: Do not use the development server in a production environment"

**How does Gunicorn help?**  
Gunicorn spawns multiple **worker processes** (each is a separate Python process that can handle one request). With 4 workers, 4 users can be served simultaneously. It handles all the complexity of process management, graceful restarts, and connection handling.

Deploy command on Render:
```bash
gunicorn app:app
```
This tells Gunicorn to import `app.py` and run the `app` Flask object.

---

## 5. All Dependencies Explained

| Package | Purpose | Used In | If Removed |
|---------|---------|---------|------------|
| `flask` | Web framework — routes, templates, sessions | `app.py`, all routes | App won't start |
| `flask-mail` | Email sending via SMTP | `app.py`, `services/mail_service.py` | No OTP emails, no password reset |
| `flask-cors` | Cross-Origin Resource Sharing headers | `app.py` (configured at startup) | Browser may block API requests from different origins |
| `gunicorn` | Production WSGI server | Used as the start command on Render | Cannot deploy to production |
| `python-dotenv` | Loads `.env` file into environment | `app.py` | Env vars not loaded; API key missing |
| `werkzeug` | Password hashing + secure file names | `routes/auth.py`, `routes/upload.py` | Passwords stored as plain text; file upload insecure |
| `requests` | Makes HTTP calls to Groq API | `models/model_router.py` | No AI responses — entire chat feature broken |
| `sentence-transformers` | Loads and runs the text embedding model | `models/embedding_manager.py` | Document search and RAG completely broken |
| `faiss-cpu` | Vector similarity search | `memory/document_store.py`, `memory/faiss_store.py` | Cannot build or search document index |
| `numpy` | Numerical array operations for FAISS vectors | `memory/document_store.py`, `memory/faiss_store.py` | FAISS cannot operate; embedding vectors have no format |
| `pypdf` | Extract text from PDF files | `memory/document_store.py` | Cannot process uploaded PDFs |
| `python-docx` | Extract text from DOCX files | `memory/document_store.py` | Cannot process uploaded Word documents |
| `fpdf2` | Generate PDF files for chat export | `routes/sessions.py` | PDF export button does nothing |
| `accelerate` | Optimizes model loading for `sentence-transformers` | Loaded automatically by `sentence-transformers` | Embedding model may fail to load or load slowly |

---

## 6. Database Schema

The SQLite database is stored at `data/chats.db`. It has three tables:

---

### Table: `chats`

Stores one row per conversation.

| Column | Type | Description |
|--------|------|-------------|
| `chat_id` | TEXT (PRIMARY KEY) | A UUID v4 string — unique identifier for this chat |
| `title` | TEXT | Display name shown in the sidebar (default: "New Chat", auto-set from first message) |
| `is_private` | INTEGER | `0` = normal chat, `1` = private (never shown or queried, currently always 0 on creation) |
| `created_at` | TEXT | ISO 8601 timestamp of when the chat was created |
| `is_pinned` | INTEGER | `0` = not pinned, `1` = pinned (pinned chats appear at top of sidebar) |
| `summary` | TEXT | Unused text column (reserved for future auto-summary feature) |
| `user_id` | INTEGER | Foreign key to `users.id` — added via migration; tracks which user owns the chat |

---

### Table: `messages`

Stores every individual message within a chat.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PRIMARY KEY AUTOINCREMENT) | Auto-incrementing message ID |
| `chat_id` | TEXT | Foreign key to `chats.chat_id` — which conversation this message belongs to |
| `role` | TEXT | Either `"user"` (human) or `"assistant"` (AI) |
| `content` | TEXT | The full text of the message |
| `timestamp` | TEXT | ISO 8601 timestamp of when the message was stored |

**Relationship:** Each `chat_id` in `messages` must exist in `chats.chat_id`. If a chat is deleted, its messages are deleted too (handled in code with explicit DELETE statements).

---

### Table: `users`

Stores user account information.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PRIMARY KEY AUTOINCREMENT) | Unique user ID — stored in Flask session after login |
| `name` | TEXT | Display name shown in the sidebar and profile |
| `email` | TEXT (UNIQUE) | Email address — used for login and all emails |
| `password_hash` | TEXT | Werkzeug PBKDF2 hash of the user's password — never the plain-text password |
| `is_verified` | INTEGER | `0` = email not verified, `1` = verified — users cannot log in until `1` |
| `otp` | TEXT | The current 6-digit OTP code sent to the user's email |
| `otp_expiry` | TEXT | ISO 8601 timestamp when the OTP expires (10 minutes after sending) |
| `otp_attempts` | INTEGER | Count of how many times the user has tried an OTP — blocked at 5 attempts |
| `reset_token` | TEXT | A random URL-safe 32-character string sent in password reset emails |
| `reset_token_expiry` | TEXT | ISO 8601 timestamp when the reset token expires (15 minutes) |
| `created_at` | TEXT | ISO 8601 timestamp of account creation — shown on the profile page |

---

## 7. API Endpoints — Complete Reference

### Authentication Endpoints

---

**`POST /api/auth/register`**  
**File:** `routes/auth.py`  
**Request body:** `{ "name": "Alice", "email": "alice@example.com", "password": "secret123" }`  
**What it does:**
1. Validates name ≥ 2 chars, valid email format, password ≥ 8 chars with at least one digit
2. Checks if email already exists and is verified → returns error
3. If email exists but unverified → sends a fresh OTP
4. Creates user record, hashes password, generates OTP, sends OTP email
**Response:** `{ "success": true, "message": "OTP sent to your email" }`

---

**`POST /api/auth/verify-otp`**  
**File:** `routes/auth.py`  
**Request body:** `{ "email": "alice@example.com", "otp": "123456" }`  
**What it does:**
1. Looks up user by email
2. Checks attempt count (blocks at 5)
3. Increments attempt counter
4. Checks if OTP has expired
5. Compares submitted OTP with stored OTP
6. On success: marks user verified, sets Flask session, sends welcome email
**Response:** `{ "success": true, "message": "Account verified" }`

---

**`POST /api/auth/resend-otp`**  
**File:** `routes/auth.py`  
**Request body:** `{ "email": "alice@example.com" }`  
**What it does:** Generates a new OTP with a fresh 10-minute expiry and sends a new email.  
**Response:** `{ "success": true }`

---

**`POST /api/auth/login`**  
**File:** `routes/auth.py`  
**Request body:** `{ "email": "alice@example.com", "password": "secret123" }`  
**What it does:**
1. Finds user by email
2. Checks `is_verified` — returns 401 with `error: "not_verified"` if unverified
3. Checks password hash with `check_password_hash`
4. On success: stores `user_id`, `user_email`, `user_name` in Flask session
**Response:** `{ "success": true, "user": {"id": 1, "name": "Alice", "email": "alice@example.com"} }`

---

**`POST /api/auth/logout`**  
**File:** `routes/auth.py`  
**What it does:** Calls `session.clear()` to remove all session data.  
**Response:** `{ "success": true }`

---

**`POST /api/auth/forgot-password`**  
**File:** `routes/auth.py`  
**Request body:** `{ "email": "alice@example.com" }`  
**What it does:** If email exists and is verified, generates a `secrets.token_urlsafe(32)` reset token with 15-minute expiry, stores it in DB, sends a reset email with a link containing the token. Always returns success (to prevent email enumeration attacks).  
**Response:** `{ "success": true, "message": "If that email exists, a reset link has been sent" }`

---

**`POST /api/auth/reset-password`**  
**File:** `routes/auth.py`  
**Request body:** `{ "token": "abc...", "password": "newpassword123" }`  
**What it does:** Looks up user by reset token, validates expiry, validates new password strength, updates the password hash, clears the reset token.  
**Response:** `{ "success": true, "message": "Password reset successful" }`

---

**`GET /api/auth/me`**  
**File:** `routes/auth.py`  
**What it does:** Returns minimal user info if logged in. Used by `app.js` on page load to populate the sidebar username and avatar.  
**Response:** `{ "success": true, "user": {"id": 1, "name": "Alice", "email": "alice@example.com"} }`

---

**`GET /api/auth/profile`**  
**File:** `routes/auth.py` — requires `@login_required`  
**What it does:** Returns full profile info including chat count and verification status.  
**Response:** `{ "success": true, "name": "Alice", "email": "...", "created_at": "...", "chat_count": 12, "is_verified": true }`

---

**`PUT /api/auth/profile`**  
**File:** `routes/auth.py` — requires `@login_required`  
**Request body:** `{ "name": "Alice Smith" }`  
**What it does:** Updates the user's display name in the database and in the current session.  
**Response:** `{ "success": true, "message": "Profile updated" }`

---

**`PUT /api/auth/change-password`**  
**File:** `routes/auth.py` — requires `@login_required`  
**Request body:** `{ "current_password": "old123", "new_password": "new456" }`  
**What it does:** Verifies current password, validates new password, updates hash in DB.  
**Response:** `{ "success": true, "message": "Password updated" }`

---

**`DELETE /api/auth/account`**  
**File:** `routes/auth.py` — requires `@login_required`  
**What it does:** Deletes all messages for the user's chats, deletes the chats, deletes the user record. Clears session.  
**Response:** `{ "success": true }`

---

### Chat Endpoints

---

**`POST /api/chat`**  
**File:** `routes/chat.py` — requires `@login_required`  
**Request body:**
```json
{
  "message": "What is machine learning?",
  "model": "llama3.1:8b",
  "session_id": "uuid-...",
  "is_private": false,
  "temperature": 0.7,
  "memory_enabled": true
}
```
**What it does:** Runs RAG retrieval, builds prompt, calls Groq API, streams SSE tokens back to browser. After streaming, saves messages and updates chat title if needed.  
**Response:** Server-Sent Events stream: `data: {"text": "Hello"}\n\n`, `data: {"metadata": {...}}\n\n`, `data: {"title": "What is machine..."}\n\n`

---

**`GET /api/chats`**  
**File:** `routes/sessions.py`  
**What it does:** Returns all non-private chats ordered by `is_pinned DESC, created_at DESC`.  
**Response:** `{ "chats": [{"chat_id": "...", "title": "...", "is_pinned": false, ...}] }`

---

**`POST /api/chat/new`**  
**File:** `routes/sessions.py`  
**Request body:** `{ "title": "New Chat" }`  
**What it does:** Inserts a new row in the `chats` table with a new UUID.  
**Response:** `{ "chat_id": "uuid-...", "title": "New Chat" }`

---

**`GET /api/chat/<id>`**  
**File:** `routes/sessions.py`  
**What it does:** Fetches the chat row and all its messages ordered by `id ASC`.  
**Response:** `{ "chat": {"chat_id": "...", "title": "...", "messages": [{"role": "user", "content": "..."}]} }`

---

**`PUT /api/chat/<id>`**  
**File:** `routes/sessions.py`  
**Request body:** `{ "title": "My Research Chat" }`  
**What it does:** Updates the `title` field in the `chats` table.  
**Response:** `{ "success": true, "title": "My Research Chat" }`

---

**`DELETE /api/chat/<id>`**  
**File:** `routes/sessions.py`  
**What it does:** Deletes messages, then the chat from SQLite. Also calls `delete_faiss_session()` to remove any FAISS index files for that session.  
**Response:** `{ "success": true }`

---

**`PUT /api/chat/<id>/pin`**  
**File:** `routes/sessions.py`  
**What it does:** Reads current `is_pinned` value, flips it (0→1 or 1→0), writes it back.  
**Response:** `{ "success": true, "is_pinned": true }`

---

**`GET /api/chats/search`**  
**File:** `routes/sessions.py`  
**Query params:** `?q=machine+learning`  
**What it does:** SQL query that joins `chats` and `messages`, searching for the query string in both `title` and `content` using `LIKE`.  
**Response:** `{ "results": [{"chat_id": "...", "title": "..."}] }`

---

**`GET /api/chat/<id>/export`**  
**File:** `routes/sessions.py`  
**Query params:** `?format=txt` or `?format=pdf`  
**What it does:** Fetches the full chat and serializes it to a TXT file or builds a PDF with `fpdf2`. Returns it as a downloadable file attachment.  
**Response:** Binary file download (`text/plain` or `application/pdf`)

---

**`POST /api/upload`**  
**File:** `routes/upload.py`  
**Request body:** `multipart/form-data` with a `file` field  
**What it does:** Saves file, generates AI insights from first 2,500 chars, starts background thread for FAISS indexing.  
**Response:** `{ "success": true, "summary": "...", "topics": [...], "questions": [...] }`

---

## 8. Authentication System — Full Explanation

### How Registration Works Step by Step

1. User fills in name, email, password, and confirm password on `/signup`
2. The client-side JavaScript checks passwords match before submitting
3. `POST /api/auth/register` is called
4. Server validates:
   - Name is at least 2 characters
   - Email matches the regex `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`
   - Password is at least 8 characters and contains at least 1 digit
5. If email already exists and is verified → reject
6. If email exists but unverified → resend OTP (handles the "registered but didn't verify" case)
7. `generate_password_hash(password)` creates a secure hash
8. `storage.create_user(name, email, password_hash)` inserts the row
9. A 6-digit OTP is generated: `str(secrets.randbelow(900000) + 100000)` — always 6 digits (100000–999999)
10. OTP is stored with a 10-minute expiry: `datetime.now() + timedelta(minutes=10)`
11. `send_otp_email()` fires a formatted HTML email

### What is OTP and Why We Use It

OTP stands for One-Time Password. It's a short code that:
- Proves the user has access to the email address they registered with
- Is generated randomly (not predictable)
- Expires quickly (10 minutes)
- Can only be used once (verified user can't be verified again)

This prevents bots from creating thousands of fake accounts and ensures every account belongs to a real person with a real email.

### How OTP Is Generated and Stored

```python
otp = str(secrets.randbelow(900000) + 100000)
expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
storage.set_user_otp(email, otp, expiry)  # writes to users table
```

`secrets.randbelow()` uses the OS's cryptographic random number generator — it cannot be predicted.

### How Email Verification Works

1. User submits their 6-digit code via the OTP input
2. Server retrieves the user record
3. Checks `otp_attempts < 5` (locked out at 5 wrong guesses)
4. Increments `otp_attempts` counter
5. Parses `otp_expiry` and checks it's in the future
6. Compares submitted OTP with stored OTP (plain string comparison)
7. On success: `storage.verify_user_email(email)` sets `is_verified = 1`, clears OTP fields
8. Flask session is created, welcome email is sent

### How Login Works

1. User submits email and password
2. `get_user_by_email(email)` retrieves the user
3. `is_verified` must be `1` — if not, returns 401 with `error: "not_verified"` (the frontend shows the OTP resend panel)
4. `check_password_hash(stored_hash, submitted_password)` — werkzeug computes the hash of the submitted password and compares to stored hash
5. On success: `session["user_id"] = user["id"]` etc. is set

### What is a Session and How Flask Sessions Work

A Flask session is a server-side mechanism that "remembers" who a user is across multiple HTTP requests. HTTP is stateless — each request is independent. Sessions solve this.

Flask stores session data as an **encrypted, signed cookie** in the user's browser. The cookie contains `session_id` → user data mapping. The `SECRET_KEY` in `.env` is used to sign and encrypt this cookie, so it cannot be tampered with.

When a request arrives, Flask decrypts the cookie and makes `session["user_id"]` available. The `@login_required` decorator reads this to verify the user is logged in.

### How Password Hashing Works

```
User types:  "mypassword123"
             ↓
werkzeug generates a random "salt" (extra random data)
             ↓
Runs PBKDF2-HMAC-SHA256 with 600,000 iterations
             ↓
Stored: "pbkdf2:sha256:600000$abc123xyz...[64 hex chars]"
```

The hash is **irreversible** — there's no algorithm to go from hash back to password. To verify a login, werkzeug re-runs the same algorithm with the submitted password and the stored salt, then compares outputs.

### How Forgot Password Flow Works

1. User submits their email on `/forgot-password`
2. Server checks if email exists and is verified
3. If yes: `secrets.token_urlsafe(32)` generates a 43-character random URL-safe token (e.g., `abc123Xyz...`)
4. Token is stored in `reset_token` column with a 15-minute expiry in `reset_token_expiry`
5. A reset link is constructed: `{BASE_URL}/reset-password?token={token}`
6. `send_reset_email()` sends a styled HTML email with a button linking to this URL
7. Server **always** returns success (prevents attackers from testing which emails are registered)

On the reset page:
1. The token is read from `window.location.search` in JavaScript
2. User enters new password twice
3. `POST /api/auth/reset-password` is called with `{ token, password }`
4. Server looks up user by token, validates expiry, validates password strength
5. Updates `password_hash`, clears `reset_token` and `reset_token_expiry`

### What @login_required Does

```python
@auth_bp.route("/api/auth/profile", methods=["GET"])
@login_required  # ← this runs first, before the function
def get_profile():
    ...
```

Python decorators wrap a function with additional logic. `@login_required` adds a check at the start of the function: "is `user_id` in the session?" If not, it returns a 401 error immediately without running the actual function. This protects sensitive endpoints from unauthenticated access.

---

## 9. Chat System — Full Explanation

### What Happens When a User Sends a Message

1. User presses Enter or clicks the send button
2. `sendMessage(text)` in `app.js` is called
3. The user's message is immediately shown in the chat (optimistic UI)
4. A "Thinking..." placeholder bot message bubble is created
5. An `AbortController` is created (allows cancelling the stream)
6. `isStreaming = true` — prevents sending another message while streaming
7. A `fetch()` POST to `/api/chat` is made with the message, model, session ID, etc.
8. The backend builds the prompt and calls Groq API
9. The `ReadableStream` from `response.body` is read chunk by chunk

### What is SSE (Server-Sent Events)?

SSE is a web standard for **one-way real-time data streaming** from server to client over a single HTTP connection. The server keeps the connection open and sends data whenever it has something new. Each "event" is a line like:
```
data: {"text": "Hello"}\n\n
```
The double newline signals the end of one event. The browser's `fetch` API can read these as they arrive using `response.body.getReader()`.

Unlike WebSockets (which are two-way), SSE only goes server → client, which is exactly what streaming chat responses need.

### How Streaming Works Technically

On the server (Python generator):
```python
def generate():
    for line in response.iter_lines():   # Groq streams to us
        if line.startswith("data: "):
            chunk = line[6:]
            if chunk == "[DONE]": break
            data = json.loads(chunk)
            token = data["choices"][0]["delta"].get("content", "")
            if token:
                yield f"data: {json.dumps({'text': token})}\n\n"  # we stream to browser
```

On the client (JavaScript):
```javascript
const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // parse SSE lines, append to chat bubble
}
// When done, render full text as Markdown
textContent.innerHTML = renderMarkdown(fullText);
```

While streaming: text is shown as plain text for performance. After streaming completes: the full text is rendered as Markdown (code blocks, bold, lists, etc.).

### How Chat History Is Saved

After the generator finishes streaming (the `for chunk in ask_llm_stream(...)` loop ends):
```python
if not is_private and session_id:
    storage.append_message(session_id, "user", message)
    storage.append_message(session_id, "assistant", full_response)
```

Both the user message and the complete AI response are written to the `messages` table.

### What Is Private Mode and How It Works

- **Server side:** When `is_private: true` is in the request body, `memory_enabled` is forced to False, RAG is skipped, and the final `storage.append_message()` calls are never reached. Nothing is saved.
- **Client side:** The `privateMessages` JavaScript array holds the conversation in browser memory only. When the tab is closed, it's gone. The sidebar does not reload (no session to show). The privacy warning banner is visible.

### How Memory Context Works (Last 6 Messages)

When `memory_enabled` is true and `session_id` is provided:
```python
chat = storage.get_chat(session_id)
messages = chat.get("messages", [])[-6:]  # last 6 messages
for m in messages:
    chat_context_lines.append(f"{m['role'].capitalize()}: {m['content']}")
chat_context = "\n".join(chat_context_lines)
```

These 6 messages are prepended to the prompt so the AI "remembers" what was said recently in the conversation. The limit of 6 is a balance between context quality and staying within Groq's token limits.

### How the Prompt Is Constructed

```
You are QUOKKA, a helpful AI assistant. Answer clearly, concisely, 
and avoid any filler sentences.

[If documents matched:]
Use the provided context when relevant. If the context is insufficient, 
answer using general knowledge while clearly distinguishing 
document-derived information from model knowledge.

Context:
[chunk 1 text]

[chunk 2 text]

[If memory enabled:]
User: [message 1]
Assistant: [response 1]
User: [message 2]
...

Question:
[user's current message]

Answer:
```

---

## 10. RAG Pipeline — Full Explanation

### What File Formats Are Supported

- **`.txt`** — plain text, read with standard `open()`
- **`.pdf`** — extracted with `pypdf.PdfReader`, reads each page's text
- **`.docx`** — extracted with `python-docx.Document`, reads each paragraph

### How Text Is Extracted

```python
elif ext == ".pdf":
    reader = PdfReader(file_path)
    for page in reader.pages:
        text += page.extract_text() + "\n"
elif ext == ".docx":
    doc = Document(file_path)
    for para in doc.paragraphs:
        text += para.text + "\n"
```

### What Is Chunking and Why We Do It

Language models have a **context limit** — they can only process a certain number of words at once. Also, embedding a 50-page document as a single vector would lose all specificity. We need to be able to say "this specific paragraph is relevant," not "this entire document is relevant."

Chunking splits the text into pieces. QUOKKA uses **paragraph-aware chunking**:
1. First, split by double newlines (paragraph boundaries)
2. Accumulate paragraphs until the chunk reaches ~400 words
3. If a single paragraph exceeds 400 words, split it by sentences
4. Each resulting chunk is a standalone, searchable unit

### How Embeddings Are Generated

```python
vectors = self.get_model().encode(
    file_chunks,
    batch_size=64,
    normalize_embeddings=True   # L2-normalize so cosine similarity = dot product
)
vectors = np.array(vectors).astype("float32")  # FAISS requires float32
```

The embedding model converts each chunk into a vector of 384 floats. Normalized means the vector's magnitude is 1.0, which makes the math for similarity calculations simpler and more consistent.

### How the FAISS Index Is Built

```python
self.index = faiss.IndexFlatL2(self.dimension)  # exact L2 distance search
self.index.add(vectors)                          # add all chunk vectors
faiss.write_index(self.index, self.index_path)  # persist to disk
np.save(self.chunks_path, np.array(self.chunks)) # save text chunks
np.save(self.sources_path, np.array(self.sources)) # save filenames
```

`IndexFlatL2` does an exact (brute-force) search — for every query, it computes the distance to every stored vector. This is perfectly fine for up to tens of thousands of chunks. For millions of chunks, approximate search algorithms (HNSW, IVF) would be used.

### How Similarity Search Works

```python
vec = self.get_model().encode([query], normalize_embeddings=True)
vec = np.array(vec).astype("float32")
distances, indices = self.index.search(vec, k=5)
# distances: [[0.12, 0.34, 0.67, 0.89, 1.20]]
# indices:   [[42,   17,   3,    88,   25 ]]
```

FAISS returns the indices of the 5 nearest stored vectors and their L2 distances. Lower distance = more similar.

### What Is the Similarity Threshold

After retrieval, chunks are filtered:
```python
cos_sim = 1 - (r["score"] / 2)   # convert L2 distance to cosine similarity
if cos_sim > 0.55:                # only keep chunks ≥ 55% similar
    filtered_results.append(r)
```

With normalized vectors, L2 distance and cosine similarity are related: `cos_sim = 1 - (L2² / 2)`. A threshold of 0.55 means we only use chunks that are at least 55% conceptually similar to the query. This prevents irrelevant content from confusing the AI.

### How Retrieved Context Is Injected into Prompt

```python
context_parts = [r["text"] for r in filtered_results]
doc_context = "\n\n".join(context_parts)
doc_context_text = f"""
Use the provided context when relevant...

Context:
{doc_context}
"""
```

This text block is inserted into the prompt between the system instruction and the chat history.

### What Is the Confidence Score and How It's Calculated

```python
avg_distance = sum(r["score"] for r in filtered_results) / len(filtered_results)
cosine_sim = 1 - (avg_distance / 2)
confidence_pct = max(0, round(cosine_sim * 100, 1))
```

The confidence score is the average cosine similarity of the retrieved chunks, expressed as a percentage. A 90% confidence means the retrieved passages are very strongly related to the query. This is shown in the frontend below the AI's answer: `📊 Confidence: 87.3%`.

---

## 11. Frontend Explanation

### How the UI Is Structured

The main chat page (`index.html`) uses a two-column CSS layout:
- **Left column** (`.sidebar`): chat history list, search box, new chat button, user avatar + logout button
- **Right column** (`.main-content`): top header (model selector, export buttons, private toggle), chat messages area, input box with file upload, footer

No JavaScript framework is used — everything is plain ("vanilla") HTML, CSS, and JavaScript. This keeps the bundle size minimal and eliminates build steps.

### What app.js Does

`app.js` is the complete frontend logic for the chat page (619 lines). It initializes all event listeners inside a `DOMContentLoaded` callback and manages:

| Responsibility | How |
|---|---|
| Sending messages | `sendMessage(text)` builds the payload and calls `/api/chat` |
| Streaming SSE | `ReadableStream` + `TextDecoder` in a `while(true)` loop |
| Rendering Markdown | `marked.parse(text)` after stream ends |
| Session management | `loadSessions()`, `startNewChat()`, `switchSession()` |
| File upload | `FormData` POST to `/api/upload` |
| Private mode | `updatePrivacyMode(bool)` toggles UI + resets state |
| Export | Opens `/api/chat/{id}/export?format=txt/pdf` in a new tab |
| Settings modal | Shows/hides a modal with temperature slider and memory toggle |
| XSS protection | User messages use `textContent`, not `innerHTML` |
| 401 interception | Overwrites `window.fetch` to redirect to `/login` on 401 |
| Auto-resize textarea | `scrollHeight` technique |
| Action buttons | Copy and Regenerate buttons added after each bot message |

### How SSE Streaming Is Handled in JavaScript

The key technique is reading chunks from a `ReadableStream`:

```javascript
const reader = response.body.getReader();
const decoder = new TextDecoder("utf-8");
let buffer = "";

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");  // SSE events separated by double newline
    buffer = lines.pop();               // keep incomplete event in buffer
    for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = JSON.parse(line.slice(6));
        if (data.text) {
            fullText += data.text;
            textContent.textContent = fullText;  // plain text while streaming
        }
    }
}
textContent.innerHTML = renderMarkdown(fullText);  // markdown after done
```

### How Markdown Rendering Works

QUOKKA uses `marked.js` (loaded from CDN) to render Markdown in bot responses:
```javascript
function renderMarkdown(text) {
    if (typeof marked !== "undefined") {
        return marked.parse(text);
    }
    // Fallback if CDN fails: escape HTML and replace newlines with <br>
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;")...
}
```

Markdown is **only applied to bot messages**, never to user messages. User messages use `textContent` (which escapes HTML automatically), preventing XSS attacks where a user types `<script>alert('hacked')</script>`.

### How the Model Dropdown Works

The dropdown in the header has four options with `value` attributes matching keys in `GROQ_MODEL_MAP`:
```html
<select id="model-select" class="dropdown">
    <option value="llama3.1:8b">LLaMA 3.1 8B ⚡</option>
    <option value="llama3.1:70b">LLaMA 3 70B 🔥</option>
    ...
</select>
```

When the user sends a message, `modelSelect.value` is included in the POST body. The backend maps it to the actual Groq model ID via `GROQ_MODEL_MAP`.

### How Private Mode Toggle Works

```javascript
privacyCheckbox.addEventListener("change", (e) => {
    updatePrivacyMode(e.target.checked);
});

function updatePrivacyMode(isPrivate) {
    if (isPrivate) {
        document.body.classList.add("privacy-mode");
        privateWarning.style.display = "flex";
        privateMessages = [];  // clear in-memory history
        startNewChat();        // create a blank session (no DB entry)
    } else {
        document.body.classList.remove("privacy-mode");
        privateWarning.style.display = "none";
        startNewChat();        // create a normal DB-backed session
    }
}
```

In private mode, `startNewChat()` sets `currentSessionId = null` and exits early without making an API call. Messages sent without a `session_id` are not saved by the backend.

### How File Upload Works

```javascript
fileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    // Show file name and "Indexed ✓" indicator
});
```

The file is sent as `multipart/form-data`. The backend handles processing asynchronously.

### What auth.js Does

`auth.js` is a shared utility library included by all auth pages via `<script src="/static/js/auth.js">`. It provides:

- **`postJson(url, data)`** — wrapper around `fetch()` that adds JSON headers and handles network errors
- **`togglePasswordVisibility(inputId, iconId)`** — show/hide password in any input field
- **`checkPasswordStrength(password)`** — returns score (1/2/3) and label (Weak/Medium/Strong) based on length, digits, special chars
- **`updateStrengthBar(password, barId, labelId)`** — updates the visual strength bar width and color in real time
- **`setupOTPInputs(containerSelector)`** — makes 6 individual OTP boxes behave as one: auto-advances focus, handles Backspace, handles paste (pastes all 6 digits at once)
- **`startResendCountdown(buttonId, seconds)`** — disables the Resend OTP button and shows a countdown from 60
- **`showError(elementId, message)`** / **`hideError(elementId)`** / **`showSuccess(elementId, message)`** — utility display helpers

---

## 12. Security Features

### Password Hashing (Werkzeug PBKDF2-HMAC-SHA256)
Passwords are never stored in plain text. Even if the database is leaked, passwords cannot be recovered without brute-force cracking, which is made intentionally slow by the 600,000-iteration key derivation.

### OTP Expiry — 10 Minutes
OTPs stored in `otp_expiry` are validated on every verification attempt. Expired OTPs are rejected with a clear error message.

### OTP Attempt Limiting — 5 Maximum
`otp_attempts` is incremented on every verification attempt. At 5 failed attempts, the unverified account is **deleted** from the database entirely (forcing the user to register again with a fresh OTP). This prevents brute-force OTP guessing.

### Session-Based Authentication
User identity is maintained via encrypted Flask sessions stored in the browser cookie. The cookie is signed with `SECRET_KEY` — tampered cookies are rejected.

### Login Required Protection
All profile and account management routes are decorated with `@login_required`. Unauthenticated requests receive a 401 response.

### Private Mode — No Server Storage
In private mode, the backend explicitly skips all `storage.append_message()` calls. No conversation data touches the database. The privacy is enforced server-side (not just client-side).

### Email Verification Before Login
`is_verified` must be `1` for login to succeed. Unverified accounts cannot access any protected resources.

### Reset Token Expiry — 15 Minutes
Password reset tokens are stored with a 15-minute expiry. After use, the token is cleared from the database immediately (cannot be reused).

### No Email Enumeration
The `/api/auth/forgot-password` endpoint always returns the same success message regardless of whether the email exists. An attacker cannot use this endpoint to discover which emails are registered.

### XSS Prevention — textContent vs innerHTML
User-generated text (chat messages) is always inserted using `textContent`, which escapes all HTML. Only trusted AI-generated text (which has its own content safety) uses `innerHTML` via `renderMarkdown()`.

### `debug=False` in Production
Flask's debug mode exposes an interactive debugger in the browser. Setting `debug=False` (as done in `app.py`) prevents any internal code from being exposed to users.

### Secure Filename on Upload
`werkzeug.utils.secure_filename()` strips all path components (`../`, `/`), null bytes, and special characters from uploaded filenames, preventing path traversal attacks.

---

## 13. Environment Variables

Create a file named `.env` in the project root with these variables:

### `SECRET_KEY`
**What it controls:** Flask uses this to cryptographically sign and encrypt session cookies. If this key leaks, attackers could forge session cookies and impersonate any user.  
**What happens if missing:** Flask falls back to `"quokka-dev-secret"` (hardcoded in `app.py`) — this is insecure for production because it's publicly known.  
**Example value:** `my-super-random-string-here-12345`  
**How to generate:** `python -c "import secrets; print(secrets.token_hex(32))"`

### `MAIL_USERNAME`
**What it controls:** The Gmail address that QUOKKA sends emails from.  
**What happens if missing:** All email sending fails — registration OTPs and password resets won't work.  
**Example value:** `yourapp@gmail.com`

### `MAIL_PASSWORD`
**What it controls:** The Gmail App Password (not your regular Gmail password).  
**What happens if missing:** Authentication to Gmail SMTP fails — all emails fail.  
**Example value:** `abcd efgh ijkl mnop` (16-character App Password)  
**Note:** Generate at Google Account → Security → 2-Step Verification → App Passwords

### `GROQ_API_KEY`
**What it controls:** Authentication for the Groq AI API. Every request to Groq must include this key in the `Authorization` header.  
**What happens if missing:** All chat requests return a 401 error from Groq — the AI feature stops working entirely.  
**Example value:** `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`  
**How to get:** Sign up free at [console.groq.com](https://console.groq.com)

### `BASE_URL`
**What it controls:** The base URL of the running application, used to construct password reset links in emails.  
**What happens if missing:** Defaults to `http://localhost:8000` — password reset emails will have broken links in production.  
**Example value:** `https://your-app.onrender.com` (for Render deployment)

### `MAIL_SERVER` / `MAIL_PORT`
**What they control:** The SMTP server address and port. Both have sensible defaults (`smtp.gmail.com`, `587`) already set in `app.py`, so these rarely need to be set.

### `PORT`
**What it controls:** The port the Flask development server listens on.  
**Default:** `8000` (set in `app.py`: `int(os.environ.get("PORT", 8000))`)

---

## 14. Deployment Plan

### Why Render Was Chosen

Render is a cloud platform that:
- Has a generous free tier for web services
- Automatically detects Python apps and knows to use `pip install -r requirements.txt`
- Supports environment variables through a UI
- Automatically redeploys when you push to GitHub
- Provides HTTPS out of the box
- Doesn't require any server management knowledge

### Step-by-Step Deployment Instructions

**Step 1: Prepare Your Repository**

Ensure your `.gitignore` excludes sensitive files:
```
.env
venv/
__pycache__/
data/
*.npy
*.faiss
```

**Step 2: Push to GitHub**
```bash
git init
git add .
git commit -m "Initial QUOKKA commit"
git branch -M main
git remote add origin https://github.com/your-username/QUOKKA.git
git push -u origin main
```

**Step 3: Create a Render Web Service**
1. Go to [render.com](https://render.com) and sign in
2. Click "New +" → "Web Service"
3. Connect your GitHub account and select the QUOKKA repository
4. Render will auto-detect it as a Python app

**Step 4: Configure the Build**
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Python Version:** 3.10 or higher

**Step 5: Set Environment Variables**

In the Render dashboard, go to your service → Environment → Add the following:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | A long random string |
| `MAIL_USERNAME` | your-gmail@gmail.com |
| `MAIL_PASSWORD` | Your 16-char App Password |
| `GROQ_API_KEY` | gsk_... |
| `BASE_URL` | https://your-service-name.onrender.com |

**Step 6: Deploy**
Click "Deploy" — Render will install dependencies and start Gunicorn. Your app will be live at `https://your-service-name.onrender.com`.

### What Gunicorn Does in Production

```bash
gunicorn app:app
# Reads as: "run the `app` object from `app.py` using Gunicorn"
```

Gunicorn spawns (by default) 2× CPU cores + 1 worker processes. On Render's free tier (0.1 CPU), you'll get 1-2 workers. Each worker can handle one request at a time, so with 2 workers, 2 users can be served simultaneously.

### Production Considerations

- **Database persistence:** Render's free tier does not include persistent storage. The SQLite `data/chats.db` file and FAISS indexes in `memory/doc_data/` will be **lost on every redeploy or restart**. To fix this, add a Render Disk ($7/month) or migrate to an external database.
- **Environment variables:** Never commit `.env` to Git. Always set secrets via the Render dashboard.
- **debug=False:** Already set in `app.py` — Flask's debugger is not exposed in production.

---

## 15. Known Limitations & Future Improvements

### Current Limitations

**SQLite won't scale beyond a small user base**  
SQLite handles reads well but serializes writes. With 10+ concurrent users actively chatting, write locks could cause delay. For >50 simultaneous users, migrate to PostgreSQL.

**Free Render tier sleeps after inactivity**  
Render's free tier spins down the server after 15 minutes of no traffic. The next request wakes it up but takes 30–60 seconds (the loading spinner will show for a while). Paid tier eliminates this.

**FAISS index is lost on Render redeploy without a persistent volume**  
Every time the service restarts or redeploys, the `memory/doc_data/` folder is wiped. Users would need to re-upload all documents. Fix: Render Disk mounted at the `memory/` path.

**No rate limiting on API endpoints**  
Any user (or bot) can send unlimited messages per second. This could exhaust Groq API rate limits or overload the server. Flask-Limiter can add per-IP rate limiting.

**Per-user document isolation does not exist**  
All uploaded documents go into a single shared FAISS index. Every user can potentially influence the document context for other users. The architecture needs per-user or per-chat document namespacing.

**The FaissStore per-session memory is not active**  
`memory/faiss_store.py` exists but is not used in the chat pipeline. Long conversations rely only on the last 6 messages, which means the AI can "forget" earlier parts of a long conversation.

**Mobile UI is partially complete**  
The sidebar collapses on small screens via media queries in `styles.css`, but the mobile experience has not been polished.

### Future Improvements to Consider

| Improvement | Why | How |
|---|---|---|
| Switch to PostgreSQL | Handles concurrent writes at scale | Use `psycopg2` + SQLAlchemy, set `DATABASE_URL` on Render |
| Add rate limiting | Prevent abuse, protect Groq API quota | Flask-Limiter with Redis backend |
| Persistent volume for FAISS | Don't lose document indexes on restart | Render Disk at `/data` mount path |
| Per-user document isolation | Security and relevance | Namespace FAISS indexes by `user_id` |
| Activate FaissStore | Semantic long-term memory | Wire `store_message()`/`retrieve_context()` in `routes/chat.py` |
| PWA support | Install as an app, offline support | Add `manifest.json` and a service worker |
| Chat sharing | Share a read-only link to a conversation | Generate a public share token, new `/share/<token>` route |
| Streaming document processing feedback | Show indexing progress | WebSocket or SSE progress events from `process_file()` |
| Model-specific prompt templates | Better results from each model | Different system prompts per model in `model_router.py` |
| Multi-language support | International users | i18n library, language selector |

---

## 16. Glossary

**API (Application Programming Interface)**  
A way for two programs to communicate with each other over the internet. One program sends a request (like "generate a response to this text") and the other sends back a response. QUOKKA uses the Groq API to talk to AI models.

**LLM (Large Language Model)**  
An AI system trained on huge amounts of text data that can understand and generate human language. Examples: GPT-4, LLaMA, Gemma. QUOKKA uses LLaMA and Gemma models via Groq.

**Parameters (in context of AI models)**  
The billions of mathematical "knobs" inside a neural network. Each parameter is a number that was set during training. More parameters generally means smarter behavior. "8B" means 8 billion parameters.

**Token**  
The unit of text that language models work with. A token is roughly 3-4 characters or 0.75 words. "Hello world" is 2 tokens. Models charge per token and have token limits. In QUOKKA, max_tokens is set to 512 for chat responses.

**Streaming**  
Sending data in small pieces as it becomes available, rather than waiting for everything to be ready. QUOKKA uses streaming so AI responses appear word by word instead of all at once after a long wait.

**RAG (Retrieval Augmented Generation)**  
A technique where relevant documents are retrieved and given to an AI as context before it generates an answer. This allows the AI to answer questions about documents it was never trained on.

**Vector**  
A list of numbers that represents something — in QUOKKA's case, the "meaning" of a piece of text. Two pieces of text with similar meaning will have similar vectors (their numbers will be close to each other mathematically).

**Embedding**  
The process of converting text into a vector. The embedding model (`BAAI/bge-small-en-v1.5`) does this. "Embedding" can also refer to the resulting vector itself.

**FAISS (Facebook AI Similarity Search)**  
A library that stores many vectors and can find the most similar ones to a query vector very quickly. QUOKKA uses it to find document chunks most relevant to a user's question.

**OTP (One-Time Password)**  
A short code (in QUOKKA's case, 6 digits) that is generated randomly, sent to a user's email, and can only be used once before it expires. Used to verify that a user actually owns the email address they registered with.

**Session**  
A way to "remember" a user across multiple web requests. HTTP is stateless (each request is independent), but sessions allow a server to say "this request is from user Alice." Flask sessions are stored as encrypted cookies in the user's browser.

**Hashing**  
A mathematical transformation that converts data (like a password) into a fixed-length string of characters. It is one-way: you cannot reverse a hash to get the original data. QUOKKA hashes passwords using PBKDF2-HMAC-SHA256 via Werkzeug.

**SMTP (Simple Mail Transfer Protocol)**  
The standard internet protocol for sending email between servers. QUOKKA uses Gmail's SMTP server (`smtp.gmail.com:587`) to send OTP and password reset emails.

**SSE (Server-Sent Events)**  
A web standard for one-way real-time streaming from server to browser over a regular HTTP connection. The server sends events (lines of text) as they become available. QUOKKA uses SSE to stream AI response tokens to the browser in real time.

**Blueprint (Flask)**  
A way to organize a Flask application into separate modules. Each Blueprint has its own routes, and they're all registered with the main `app` object. QUOKKA has four blueprints: `auth_bp`, `chat_bp`, `sessions_bp`, `upload_bp`.

**WSGI (Web Server Gateway Interface)**  
A standard specification for how Python web applications communicate with web servers. Flask is a WSGI application. Gunicorn is a WSGI server. They talk to each other using this standard interface.

**Gunicorn**  
A production-grade Python WSGI HTTP server that spawns multiple worker processes to handle concurrent requests. It's the standard way to run Flask applications in production instead of Flask's built-in development server.

---

*End of QUOKKA Project Documentation Report*  
*All information in this document was verified against the actual source code. Nothing is assumed or speculated.*
