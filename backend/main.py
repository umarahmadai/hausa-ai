import logging
import math
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.ai_service import HausaAIService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="HausaAI Pro API",
    description="Bilingual Hausa and English AI assistant API.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

ai_service = HausaAIService()

# This limiter is intentionally process-local. Use a shared Redis-backed
# limiter before running multiple instances/workers.
_request_times: dict[str, deque[float]] = defaultdict(deque)
_rate_limit_lock = threading.Lock()
_MAX_TRACKED_CLIENTS = 10_000


@app.middleware("http")
async def chat_rate_limit(request: Request, call_next):
    if request.url.path != "/ai/chat" or request.method != "POST":
        return await call_next(request)

    client_host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = settings.API_RATE_LIMIT_WINDOW_SECONDS
    limit = settings.API_RATE_LIMIT_REQUESTS

    with _rate_limit_lock:
        # Bound memory use if many distinct client addresses reach the API.
        if client_host not in _request_times and len(_request_times) >= _MAX_TRACKED_CLIENTS:
            cutoff = now - window
            stale_clients = [
                host for host, timestamps in _request_times.items()
                if not timestamps or timestamps[-1] <= cutoff
            ]
            for host in stale_clients:
                _request_times.pop(host, None)

        if client_host not in _request_times and len(_request_times) >= _MAX_TRACKED_CLIENTS:
            return JSONResponse(
                status_code=503,
                content={"detail": "The service is temporarily busy. Please try again."},
            )

        timestamps = _request_times.setdefault(client_host, deque())
        cutoff = now - window
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= limit:
            retry_after = max(1, math.ceil(window - (now - timestamps[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again shortly."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        timestamps.append(now)
        remaining = max(0, limit - len(timestamps))

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


@app.get("/")
def root():
    return {"name": "HausaAI Pro API", "status": "online", "docs": "/docs"}


@app.get("/health")
def health():
    # Liveness only: external AI providers may be temporarily unavailable.
    return {"status": "ok"}


@app.post("/ai/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        result = ai_service.chat(request.message)
        return ChatResponse(**result)
    except RuntimeError as exc:
        logger.warning("AI service unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily unavailable. Please try again.",
        ) from exc
    except Exception:
        logger.exception("Unexpected error while handling /ai/chat.")
        raise HTTPException(
            status_code=502,
            detail="The AI provider could not complete the request. Please try again.",
        ) from None
