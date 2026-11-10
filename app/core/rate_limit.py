import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitError

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def reset() -> None:
    with _lock:
        _hits.clear()


def rate_limit(request: Request) -> None:
    """Sliding window: at most N requests per client in the last W seconds."""
    if not settings.rate_limit_enabled:
        return

    client = request.client.host if request.client else "unknown"
    window = settings.rate_limit_window
    now = time.monotonic()

    with _lock:
        hits = _hits[client]
        while hits and now - hits[0] >= window:
            hits.popleft()
        if len(hits) >= settings.rate_limit_requests:
            retry_after = int(window - (now - hits[0])) + 1
            raise RateLimitError(retry_after)
        hits.append(now)