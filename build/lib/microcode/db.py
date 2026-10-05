"""SQLite storage: config, sessions, messages."""
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(os.environ.get("MINI_CC_DB", Path.home() / ".mini_cc.db"))
# DB_PATH_TEST = ".mini_cc.db"
db = sqlite3.connect(DB_PATH)
db.executescript("""
CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY, title TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id),
  role TEXT, content TEXT, created_at REAL);
""")
try:
    os.chmod(DB_PATH, 0o600)  # the API key lives in this file
except OSError:
    pass


# ------------------------------------------------------------------ config
def cfg_get():
    return dict(db.execute("SELECT key, value FROM config"))


def cfg_set(**kv):
    with db:
        db.executemany("INSERT INTO config VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       [(k, v or "") for k, v in kv.items()])


# ---------------------------------------------------------------- sessions
def new_session(title="New chat"):
    with db:
        return db.execute("INSERT INTO sessions(title, created_at) VALUES(?, ?)", (title, time.time())).lastrowid


def session_exists(sid):
    return db.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone() is not None


def list_sessions(limit=15):
    """Rows of (id, title, message_count, created_at); empty sessions are hidden."""
    return db.execute("""SELECT s.id, s.title, COUNT(m.id), s.created_at FROM sessions s
                         JOIN messages m ON m.session_id = s.id
                         GROUP BY s.id ORDER BY s.id DESC LIMIT ?""", (limit,)).fetchall()


# ---------------------------------------------------------------- messages
def load_messages(sid):
    rows = db.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id", (sid,))
    return [{"role": r, "content": json.loads(c)} for r, c in rows]


def push(sid, history, msg):
    """Append a message to the in-memory history and persist it."""
    history.append(msg)
    with db:
        db.execute("INSERT INTO messages(session_id, role, content, created_at) VALUES(?,?,?,?)",
                   (sid, msg["role"], json.dumps(msg["content"]), time.time()))
