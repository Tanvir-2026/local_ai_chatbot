import sqlite3

from app.core.exceptions import ConversationNotFoundError
from app.models import conversation as conversation_model
from app.models import usage as usage_model


def _with_total(row: dict) -> dict:
    row["total_tokens"] = row["prompt_tokens"] + row["completion_tokens"]
    return row


def get_usage(db: sqlite3.Connection, conversation_id: str | None) -> dict:
    if conversation_id and not conversation_model.get(db, conversation_id):
        raise ConversationNotFoundError()
    return {
        "conversation_id": conversation_id,
        "total": _with_total(usage_model.totals(db, conversation_id)),
        "by_model": [
            _with_total(r) for r in usage_model.by_model(db, conversation_id)
        ],
    }