import sqlite3

_STATS = """
    COUNT(*)                                       AS requests,
    COALESCE(SUM(prompt_tokens), 0)                AS prompt_tokens,
    COALESCE(SUM(completion_tokens), 0)            AS completion_tokens,
    ROUND(AVG(duration_ms), 1)                     AS avg_response_time_ms,
    ROUND(1000.0 * SUM(CASE WHEN completion_tokens IS NOT NULL AND duration_ms > 0
                            THEN completion_tokens END)
          / NULLIF(SUM(CASE WHEN completion_tokens IS NOT NULL AND duration_ms > 0
                            THEN duration_ms END), 0), 2) AS avg_tokens_per_second
"""


def _where(conversation_id: str | None) -> tuple[str, tuple]:
    if conversation_id:
        return "WHERE role = 'assistant' AND conversation_id = ?", (conversation_id,)
    return "WHERE role = 'assistant'", ()


def totals(db: sqlite3.Connection, conversation_id: str | None = None) -> dict:
    where, params = _where(conversation_id)
    row = db.execute(f"SELECT {_STATS} FROM messages {where}", params).fetchone()
    return dict(row)


def by_model(db: sqlite3.Connection, conversation_id: str | None = None) -> list[dict]:
    where, params = _where(conversation_id)
    rows = db.execute(
        f"""
        SELECT COALESCE(model, 'unknown') AS model, {_STATS}
        FROM messages {where}
        GROUP BY COALESCE(model, 'unknown')
        ORDER BY requests DESC
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]