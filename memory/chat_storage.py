import os
import uuid
import json
import sqlite3
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "chats.db")
LEGACY_JSON_PATH = os.path.join(DATA_DIR, "chats.json")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def init_storage():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    conn = get_connection()
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
        chat_id TEXT PRIMARY KEY,
        title TEXT,
        is_private INTEGER DEFAULT 0,
        created_at TEXT,
        is_pinned INTEGER DEFAULT 0,
        summary TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT,
        role TEXT,
        content TEXT,
        timestamp TEXT,
        FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_verified INTEGER DEFAULT 0,
        otp TEXT,
        otp_expiry TEXT,
        otp_attempts INTEGER DEFAULT 0,
        reset_token TEXT,
        reset_token_expiry TEXT,
        created_at TEXT
    )''')
    conn.commit()

    # Add user_id to chats if missing (for per-user profile stats)
    try:
        c.execute("ALTER TABLE chats ADD COLUMN user_id INTEGER")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    
    # Migrate legacy JSON if it exists
    if os.path.exists(LEGACY_JSON_PATH):
        try:
            with open(LEGACY_JSON_PATH, "r", encoding="utf-8") as f:
                legacy_data = json.load(f)
            
            for cid, chat in legacy_data.items():
                # Insert chat
                c.execute('''INSERT OR IGNORE INTO chats (chat_id, title, is_private, created_at, is_pinned, summary)
                             VALUES (?, ?, ?, ?, ?, ?)''',
                          (chat.get("chat_id", cid), 
                           chat.get("title", "Legacy Chat"), 
                           1 if chat.get("is_private") else 0,
                           chat.get("created_at", datetime.now().isoformat()),
                           1 if chat.get("is_pinned") else 0,
                           chat.get("summary", "")))
                
                # Insert messages
                for msg in chat.get("messages", []):
                    c.execute('''INSERT INTO messages (chat_id, role, content, timestamp)
                                 VALUES (?, ?, ?, ?)''',
                              (cid, msg.get("role"), msg.get("content"), msg.get("timestamp", datetime.now().isoformat())))
            conn.commit()
            
            # Rename legacy file so we don't migrate again
            os.rename(LEGACY_JSON_PATH, LEGACY_JSON_PATH + ".bak")
            print("Successfully migrated legacy JSON chats to SQLite.")
        except Exception as e:
            print(f"Error migrating JSON to SQLite: {e}")
            
    conn.close()

def create_chat(title="New Chat", is_private=False):
    chat_id = str(uuid.uuid4())
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO chats (chat_id, title, is_private, created_at, is_pinned) VALUES (?, ?, ?, ?, ?)',
              (chat_id, title, 1 if is_private else 0, datetime.now().isoformat(), 0))
    conn.commit()
    conn.close()
    return chat_id

def get_all_chats(include_private=False):
    conn = get_connection()
    c = conn.cursor()
    if include_private:
        c.execute('SELECT * FROM chats ORDER BY is_pinned DESC, created_at DESC')
    else:
        c.execute('SELECT * FROM chats WHERE is_private = 0 ORDER BY is_pinned DESC, created_at DESC')
    
    rows = c.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

def get_chat(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id,))
    chat_row = c.fetchone()
    
    if not chat_row:
        conn.close()
        return None
        
    chat = dict(chat_row)
    chat["is_private"] = bool(chat["is_private"])
    chat["is_pinned"] = bool(chat["is_pinned"])
    
    c.execute('SELECT role, content, timestamp FROM messages WHERE chat_id = ? ORDER BY id ASC', (chat_id,))
    msg_rows = c.fetchall()
    chat["messages"] = [dict(r) for r in msg_rows]
    
    conn.close()
    return chat

def update_chat_title(chat_id, title):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE chats SET title = ? WHERE chat_id = ?', (title, chat_id))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success

def append_message(chat_id, role, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO messages (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)',
              (chat_id, role, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def delete_chat(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM messages WHERE chat_id = ?', (chat_id,))
    c.execute('DELETE FROM chats WHERE chat_id = ?', (chat_id,))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success

def toggle_pin_chat(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT is_pinned FROM chats WHERE chat_id = ?', (chat_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False
        
    new_status = 0 if row["is_pinned"] else 1
    c.execute('UPDATE chats SET is_pinned = ? WHERE chat_id = ?', (new_status, chat_id))
    conn.commit()
    conn.close()
    return bool(new_status)

def search_chats(query, include_private=False):
    conn = get_connection()
    c = conn.cursor()
    q = f"%{query}%"
    
    if include_private:
        c.execute('''
            SELECT DISTINCT c.chat_id 
            FROM chats c 
            LEFT JOIN messages m ON c.chat_id = m.chat_id 
            WHERE c.title LIKE ? OR m.content LIKE ?
        ''', (q, q))
    else:
        c.execute('''
            SELECT DISTINCT c.chat_id 
            FROM chats c 
            LEFT JOIN messages m ON c.chat_id = m.chat_id 
            WHERE c.is_private = 0 AND (c.title LIKE ? OR m.content LIKE ?)
        ''', (q, q))
        
    rows = c.fetchall()
    conn.close()
    return [r["chat_id"] for r in rows]

def update_summary(chat_id, summary):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE chats SET summary = ? WHERE chat_id = ?', (summary, chat_id))
    conn.commit()
    conn.close()

def trim_messages(chat_id, keep_recent=2):
    # This deletes all but the most recent N messages.
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?', (chat_id, keep_recent))
    rows = c.fetchall()
    if rows:
        min_id_to_keep = rows[-1]["id"]
        c.execute('DELETE FROM messages WHERE chat_id = ? AND id < ?', (chat_id, min_id_to_keep))
        conn.commit()
        
    conn.close()

def create_user(name, email, password_hash):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO users (name, email, password_hash, created_at)
           VALUES (?, ?, ?, ?)''',
        (name, email.lower().strip(), password_hash, datetime.now().isoformat()),
    )
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email.lower().strip(),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_reset_token(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE reset_token = ?', (token,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def set_user_otp(email, otp, expiry):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        '''UPDATE users SET otp = ?, otp_expiry = ?, otp_attempts = 0
           WHERE email = ?''',
        (otp, expiry, email.lower().strip()),
    )
    conn.commit()
    conn.close()


def increment_otp_attempts(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'UPDATE users SET otp_attempts = otp_attempts + 1 WHERE email = ?',
        (email.lower().strip(),),
    )
    conn.commit()
    conn.close()


def verify_user_email(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        '''UPDATE users SET is_verified = 1, otp = NULL, otp_expiry = NULL,
           otp_attempts = 0 WHERE email = ?''',
        (email.lower().strip(),),
    )
    conn.commit()
    conn.close()


def set_reset_token(email, token, expiry):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        '''UPDATE users SET reset_token = ?, reset_token_expiry = ?
           WHERE email = ?''',
        (token, expiry, email.lower().strip()),
    )
    conn.commit()
    conn.close()


def update_password(email, new_hash):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'UPDATE users SET password_hash = ? WHERE email = ?',
        (new_hash, email.lower().strip()),
    )
    conn.commit()
    conn.close()


def clear_reset_token(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        '''UPDATE users SET reset_token = NULL, reset_token_expiry = NULL
           WHERE email = ?''',
        (email.lower().strip(),),
    )
    conn.commit()
    conn.close()


def update_user_name(user_id, name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    conn.commit()
    conn.close()


def get_user_chat_count(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) AS cnt FROM chats WHERE user_id = ? AND is_private = 0",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    return int(row["cnt"]) if row else 0


def delete_user_account(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT chat_id FROM chats WHERE user_id = ?", (user_id,))
        chat_ids = [r["chat_id"] for r in c.fetchall()]
        for chat_id in chat_ids:
            c.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        c.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Initialize DB and run migrations on import
init_storage()
