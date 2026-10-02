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
        conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_key TEXT NOT NULL UNIQUE,
            notification_type TEXT NOT NULL,
            lead_id INTEGER,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            parse_mode TEXT NOT NULL DEFAULT 'HTML',
            status TEXT NOT NULL DEFAULT 'PENDING',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
            UPDATE notification_outbox
            SET status = 'PENDING', updated_at = CURRENT_TIMESTAMP
            WHERE status = 'SENDING'
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


def enqueue_notification(event_key, notification_type, lead_id, chat_id, text, parse_mode="HTML"):
    with connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO notification_outbox (
                event_key, notification_type, lead_id, chat_id, text, parse_mode
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (event_key, notification_type, lead_id, chat_id, text, parse_mode))
        row = conn.execute(
            "SELECT * FROM notification_outbox WHERE event_key = ?",
            (event_key,),
        ).fetchone()
        conn.commit()
        return row

def claim_notification(notification_id):
    with connect() as conn:
        cur = conn.execute("""
            UPDATE notification_outbox
            SET status = 'SENDING', updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'PENDING'
        """, (notification_id,))
        if cur.rowcount != 1:
            conn.commit()
            return None
        row = conn.execute(
            "SELECT * FROM notification_outbox WHERE id = ?",
            (notification_id,),
        ).fetchone()
        conn.commit()
        return row

def claim_pending_notifications(limit=20):
    with connect() as conn:
        ids = [
            row["id"]
            for row in conn.execute("""
                SELECT id FROM notification_outbox
                WHERE status = 'PENDING'
                ORDER BY id ASC
                LIMIT ?
            """, (limit,)).fetchall()
        ]

    claimed = []
    for notification_id in ids:
        row = claim_notification(notification_id)
        if row is not None:
            claimed.append(row)
    return claimed

def mark_notification_sent(notification_id):
    with connect() as conn:
        cur = conn.execute("""
            UPDATE notification_outbox
            SET status = 'SENT',
                attempts = attempts + 1,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'SENDING'
        """, (notification_id,))
        conn.commit()
        return cur.rowcount == 1

def mark_notification_failed(notification_id, error, max_attempts=5):
    with connect() as conn:
        row = conn.execute(
            "SELECT attempts, status FROM notification_outbox WHERE id = ?",
            (notification_id,),
        ).fetchone()
        if not row or row["status"] != "SENDING":
            return False

        attempts = int(row["attempts"]) + 1
        next_status = "FAILED" if attempts >= max_attempts else "PENDING"
        cur = conn.execute("""
            UPDATE notification_outbox
            SET status = ?,
                attempts = ?,
                last_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'SENDING'
        """, (next_status, attempts, str(error)[:500], notification_id))
        conn.commit()
        return cur.rowcount == 1

def outbox_stats():
    with connect() as conn:
        rows = conn.execute("""
            SELECT status, COUNT(*) AS count
            FROM notification_outbox
            GROUP BY status
        """).fetchall()
        return {row["status"]: row["count"] for row in rows}
