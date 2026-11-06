import sqlite3

from fastapi import APIRouter, Depends, Response

from app.controllers import conversation_controller as controller
from app.db.database import get_db
from app.schemas.conversation import ConversationDetail, ConversationOut

router = APIRouter(tags=["Conversations"])


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: sqlite3.Connection = Depends(get_db)):
    return controller.list_conversations(db)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, db: sqlite3.Connection = Depends(get_db)):
    return controller.get_conversation(db, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: sqlite3.Connection = Depends(get_db)):
    controller.delete_conversation(db, conversation_id)
    return Response(status_code=204)