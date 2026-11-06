import sqlite3

from fastapi import APIRouter, Depends

from app.controllers import usage_controller
from app.db.database import get_db
from app.schemas.usage import UsageResponse

router = APIRouter(tags=["Usage"])


@router.get("/usage", response_model=UsageResponse)
def get_usage(
    conversation_id: str | None = None,
    db: sqlite3.Connection = Depends(get_db),
):
    return usage_controller.get_usage(db, conversation_id)