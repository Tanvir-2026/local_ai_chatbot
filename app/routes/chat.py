import sqlite3

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.controllers import chat_controller
from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: sqlite3.Connection = Depends(get_db)):
    return chat_controller.handle_chat(db, req)


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    events = chat_controller.start_chat_stream(req)
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )