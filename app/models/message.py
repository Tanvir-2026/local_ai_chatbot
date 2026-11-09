import sqlite3

from app.db.database import utc_now


def add(
    db: sqlite3.Connection,
    conversation_id: str,
    role: str,
    content: str,
    model: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    duration_ms: int | None = None,
) -> dict:
    ts = utc_now()
    cur = db.execute(
        """
        INSERT INTO messages
            (conversation_id, role, content, model,
             prompt_tokens, completion_tokens, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (conversation_id, role, content, model,
         prompt_tokens, completion_tokens, duration_ms, ts),
    )
    return {"id": cur.lastrowid, "created_at": ts}


def list_for_conversation(db: sqlite3.Connection, conversation_id: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT id, role, content, model, prompt_tokens,
               completion_tokens, duration_ms, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id
        """,
        (conversation_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def recent(db: sqlite3.Connection, conversation_id: str, limit: int) -> list[dict]:
    """Last `limit` messages in chronological order, shaped for the LLM."""
    rows = db.execute(
        """
        SELECT role, content FROM (
            SELECT id, role, content FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
        ) ORDER BY id
        """,
        (conversation_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]

def count(db: sqlite3.Connection, conversation_id: str) -> int:
    return db.execute(
        "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,)
    ).fetchone()[0]