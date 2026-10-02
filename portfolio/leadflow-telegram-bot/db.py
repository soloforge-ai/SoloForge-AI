import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("leads.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            telegram_username TEXT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL,
            need TEXT NOT NULL,
            budget TEXT NOT NULL,
            score INTEGER NOT NULL,
            label TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

def create_lead(user_id, username, name, contact, need, budget, score, label):
    with connect() as conn:
        cur = conn.execute("""
            INSERT INTO leads (
                telegram_user_id, telegram_username, name, contact,
                need, budget, score, label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, name, contact, need, budget, score, label))
        conn.commit()
        return cur.lastrowid

def get_lead(lead_id):
    with connect() as conn:
        return conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()

def update_status(lead_id, status):
    if status not in ("APPROVED", "REJECTED"):
        raise ValueError("Invalid lead status")
    with connect() as conn:
        cur = conn.execute("""
            UPDATE leads
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'PENDING'
        """, (status, lead_id))
        conn.commit()
        return cur.rowcount == 1

def recent_leads(limit=10):
    with connect() as conn:
        return conn.execute("""
            SELECT * FROM leads
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

def stats():
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM leads WHERE status='PENDING'").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM leads WHERE status='APPROVED'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM leads WHERE status='REJECTED'").fetchone()[0]
        avg_score = conn.execute("SELECT COALESCE(AVG(score), 0) FROM leads").fetchone()[0]
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "avg_score": round(avg_score, 1),
        }
