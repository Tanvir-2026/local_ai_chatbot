import logging
import sqlite3

from app.core.config import settings
from app.core.exceptions import ConversationNotFoundError
from app.models import conversation as conversation_model
from app.models import message as message_model
from app.services import vector_service

log = logging.getLogger(__name__)


def list_conversations(db: sqlite3.Connection) -> list[dict]:
    return conversation_model.list_all(db)


def get_conversation(db: sqlite3.Connection, conversation_id: str) -> dict:
    conversation = conversation_model.get(db, conversation_id)
    if not conversation:
        raise ConversationNotFoundError()
    conversation["messages"] = message_model.list_for_conversation(db, conversation_id)
    return conversation


def delete_conversation(db: sqlite3.Connection, conversation_id: str) -> None:
    deleted = conversation_model.delete(db, conversation_id)
    if not deleted:
        raise ConversationNotFoundError()
    db.commit()

    if settings.memory_enabled:
        try:
            vector_service.delete_conversation(conversation_id)
        except Exception:
            log.warning("Could not delete ChromaDB entries", exc_info=True)