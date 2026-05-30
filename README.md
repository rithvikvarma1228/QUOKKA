# 🐨 QUOKKA AI Assistant

A fast, full-featured AI chat assistant powered by Groq — with document search, email auth, and private mode.

---

## Overview

QUOKKA is a self-hosted AI chat assistant built with Flask and Vanilla JavaScript. It uses the **Groq API** for blazing-fast LLM inference across multiple models including LLaMA and Mixtral, making responses feel near-instant compared to traditional hosted AI services.

The app features a complete user authentication system with email OTP verification, secure password reset, and persistent chat history stored in SQLite. Beyond simple Q&A, QUOKKA supports **Retrieval-Augmented Generation (RAG)** — upload a PDF, DOCX, or TXT file and the assistant will ground its answers in your document's content using FAISS vector search and the `BAAI/bge-small-en-v1.5` embedding model.

QUOKKA is designed for developers and power users who want a private, extensible, self-hostable AI assistant without paying per-token at scale. It deploys easily to Render with a single environment variable configuration.

---

## Features

- 📧 **Email authentication with OTP verification** — register with email, verify with a 6-digit OTP sent to your inbox
- 🔐 **Password reset via email** — secure tokenized reset link with 15-minute expiry
- 🤖 **AI chat with streaming responses** — real-time token streaming via Server-Sent Events
- 🧠 **Multiple LLM models via Groq API** — switch between LLaMA 3.1 8B, LLaMA 3 70B, Mixtral 8x7B, and Gemma 2 9B
- 📄 **RAG document search** — upload PDF, TXT, or DOCX files; the AI retrieves relevant passages using FAISS vector search
- 📊 **Live document intelligence** — on upload, the AI generates a summary, topic list, and suggested questions for your document
- 💬 **Persistent chat history** — all conversations stored in SQLite with full message history
- 🔍 **Chat search** — search across all chat titles and message content
- 📌 **Pin chats** — pin important conversations to the top of the sidebar
- 🔒 **Private mode** — messages are never saved to the database; zero server-side storage
- 📤 **Export chats as TXT and PDF** — download full conversation history in either format
- 👤 **Profile page** — view account info, chat count, update display name, change password, or delete account
- 🔄 **Session management** — server-side Flask sessions with login/logout
- 📝 **Markdown rendering** — AI responses rendered with `marked.js` for formatted output
- 📱 **Mobile responsive** — works cleanly across desktop and mobile screen sizes
- 🌡️ **Adjustable temperature** — control AI creativity via a settings slider
- 🧠 **Memory context toggle** — enable or disable conversation history sent to the model

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask (Python) |
| Frontend | Vanilla JS, HTML, CSS |
| AI Provider | Groq API |
| LLM Models | LLaMA 3.1 8B, LLaMA 3 70B, Mixtral 8x7B, Gemma 2 9B |
| Embeddings | BAAI/bge-small-en-v1.5 |
| Vector Search | FAISS |
| Database | SQLite |
| Email | Flask-Mail (Gmail SMTP) |
| Deployment | Render |

---

## Project Structure

```
QUOKKA/
├── app.py                        # Flask app factory, config, page routes, background warmup
│
├── routes/
│   ├── auth.py                   # Register, OTP verify, login, logout, password reset, profile
│   ├── auth_middleware.py        # @login_required decorator
│   ├── chat.py                   # /api/chat — streaming response endpoint with RAG
│   ├── sessions.py               # Chat CRUD, pin/unpin, search, export (TXT/PDF)
│   └── upload.py                 # File upload + document intelligence generation
│
├── memory/
│   ├── chat_storage.py           # SQLite operations for chats, messages, and users
│   ├── document_store.py         # Document ingestion, chunking, FAISS indexing, RAG retrieval
│   └── faiss_store.py            # Per-session FAISS store (reserved for future semantic memory)
│
├── models/
│   ├── model_router.py           # Groq API client — streaming and JSON inference functions
│   └── embedding_manager.py      # Singleton SentenceTransformer loader
│
├── services/
│   └── mail_service.py           # HTML email sending — OTP, welcome, and password reset emails
│
├── templates/
│   ├── index.html                # Main chat UI
│   ├── login.html                # Login page
│   ├── signup.html               # Registration + OTP verification page
│   ├── forgot_password.html      # Forgot password page
│   ├── reset_password.html       # Password reset page
│   └── profile.html              # User profile page
│
├── static/
│   ├── css/styles.css            # Global stylesheet
│   └── js/app.js                 # Frontend logic (chat, sessions, streaming, export)
│
├── data/                         # SQLite database (auto-created, git-ignored)
├── uploads/                      # Uploaded documents (auto-created)
├── memory/doc_data/              # FAISS document index + chunk arrays (git-ignored)
├── memory/faiss_data/            # Per-session FAISS indexes (git-ignored)
│
├── requirements.txt
├── .env                          # Environment variables (never commit this)
└── .gitignore
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Git
- A Gmail account with an **App Password** enabled (not your regular password)
- A **Groq API key** — free at [console.groq.com](https://console.groq.com)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/QUOKKA.git
   cd QUOKKA
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your `.env` file**

   Create a `.env` file in the project root (see [Environment Variables](#environment-variables) below):
   ```bash
   cp .env.example .env   # or create it manually
   ```

5. **Run the app**
   ```bash
   python app.py
   ```
   Open [http://localhost:8000](http://localhost:8000) in your browser.

---

### Environment Variables

Create a `.env` file in the project root with the following variables:

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Flask session secret key — any random string | `any-random-string` |
| `MAIL_USERNAME` | Gmail address used to send emails | `you@gmail.com` |
| `MAIL_PASSWORD` | Gmail App Password (16-character, not your login password) | `abcd abcd abcd abcd` |
| `GROQ_API_KEY` | Groq API key for LLM inference | `gsk_...` |
| `BASE_URL` | Base URL of your deployed app (used in reset password links) | `http://localhost:8000` |

> **Getting a Gmail App Password:**  
> Go to your Google Account → Security → 2-Step Verification → App Passwords. Generate one for "Mail".

> **Getting a Groq API key:**  
> Sign up free at [console.groq.com](https://console.groq.com), then create an API key.

---

## Usage

### Register & Verify Email
1. Navigate to `/signup` and fill in your name, email, and password (min 8 chars, 1 number).
2. Check your inbox for a 6-digit OTP — enter it to verify your account.
3. You'll be automatically logged in and sent a welcome email.

### Upload Documents for RAG
1. Click the **paperclip icon** in the chat input area.
2. Select a `.pdf`, `.txt`, or `.docx` file.
3. The document is processed in the background — QUOKKA will show a summary, key topics, and suggested questions.
4. Ask questions naturally; QUOKKA will retrieve relevant passages and cite them with a confidence score.

### Switch Between Models
1. Use the **model dropdown** in the top header to switch between:
   - **LLaMA 3.1 8B ⚡** — fastest responses
   - **LLaMA 3 70B 🔥** — best quality
   - **Mixtral 8x7B ⚖️** — balanced speed and quality
   - **Gemma 2 9B 💨** — efficient alternative
2. The selected model is used for all subsequent messages.

### Export Chats
- Click the **TXT** or **PDF** buttons in the header to download the current chat.
- TXT exports as plain text; PDF exports a formatted document.

### Private Mode
- Toggle **Private Chat** in the header to enable private mode.
- In private mode, no messages are saved to the server — the conversation exists only in your browser tab.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user account |
| `POST` | `/api/auth/verify-otp` | Verify email with 6-digit OTP |
| `POST` | `/api/auth/resend-otp` | Resend OTP to email |
| `POST` | `/api/auth/login` | Login with email and password |
| `POST` | `/api/auth/logout` | Logout and clear session |
| `POST` | `/api/auth/forgot-password` | Request a password reset email |
| `POST` | `/api/auth/reset-password` | Reset password using token from email |
| `GET` | `/api/auth/me` | Get current authenticated user |
| `GET` | `/api/auth/profile` | Get profile info + chat count |
| `PUT` | `/api/auth/profile` | Update display name |
| `PUT` | `/api/auth/change-password` | Change password |
| `DELETE` | `/api/auth/account` | Delete account and all data |
| `POST` | `/api/chat` | Send message, receive streaming response (SSE) |
| `GET` | `/api/chats` | Get all saved chats |
| `POST` | `/api/chat/new` | Create a new chat session |
| `GET` | `/api/chat/<id>` | Get full chat with message history |
| `PUT` | `/api/chat/<id>` | Rename a chat |
| `DELETE` | `/api/chat/<id>` | Delete a chat |
| `PUT` | `/api/chat/<id>/pin` | Toggle pin/unpin a chat |
| `GET` | `/api/chat/<id>/export` | Export chat as `?format=txt` or `?format=pdf` |
| `GET` | `/api/chats/search` | Search chats by title or message content |
| `POST` | `/api/upload` | Upload a document for RAG |

---

## Deployment

QUOKKA is designed to deploy on **[Render](https://render.com)** (free tier compatible).

1. **Push your code to GitHub** (make sure `.env` and `data/` are in `.gitignore`)

2. **Create a new Web Service on Render**
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`

3. **Set environment variables** in the Render dashboard under *Environment*:
   - `SECRET_KEY`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `GROQ_API_KEY`, `BASE_URL`

4. **Deploy** — Render will build and start the service automatically on each push to main.

> **Note:** The `data/` directory (SQLite database) and FAISS index files are ephemeral on Render's free tier. For persistent storage, mount a Render Disk or use an external database service.

---

## License

This project is licensed under the **MIT License** — free to use, modify, and distribute.

```
MIT License

Copyright (c) 2025 QUOKKA

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```