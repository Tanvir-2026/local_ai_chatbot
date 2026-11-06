from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from app.routes import chat, conversations, health, models, usage
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.security import require_api_key
from app.db.database import init_db
from app.routes import chat, conversations, health, models


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
register_exception_handlers(app)

protected = [Depends(require_api_key)]
app.include_router(health.router, prefix="/api", dependencies=protected)
app.include_router(models.router, prefix="/api", dependencies=protected)
app.include_router(chat.router, prefix="/api", dependencies=protected)
app.include_router(conversations.router, prefix="/api", dependencies=protected)
app.include_router(usage.router, prefix="/api", dependencies=protected)

@app.get("/")
def root():
    return {"status": "ok", "app": settings.app_name}