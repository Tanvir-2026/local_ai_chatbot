import sqlite3
import uuid

from app.db.database import utc_now


def create(db: sqlite3.Connection, title: str) -> dict:
    conversation_id = str(uuid.uuid4())
    ts = utc_now()
    db.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (conversation_id, title, ts, ts),
    )
    return {"id": conversation_id, "title": title, "created_at": ts, "updated_at": ts}


def get(db: sqlite3.Connection, conversation_id: str) -> dict | None:
    row = db.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
        (conversation_id,),
    ).fetchone()
    return dict(row) if row else None


def list_all(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at,
               COUNT(m.id) AS message_count
        FROM conversations c
        LEFT JOIN messages m ON m.conversation_id = c.id
        GROUP BY c.id
        ORDER BY c.updated_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def touch(db: sqlite3.Connection, conversation_id: str) -> None:
    db.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (utc_now(), conversation_id),
    )


def delete(db: sqlite3.Connection, conversation_id: str) -> bool:
    cur = db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return cur.rowcount > 0