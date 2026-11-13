from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.ai_service import HausaAIService

app = FastAPI(
    title="HausaAI Pro API",
    description="Bilingual Hausa and English AI assistant API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

ai_service = HausaAIService()


@app.get("/")
def root():
    return {"name": "HausaAI Pro API", "status": "online", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ai/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        result = ai_service.chat(request.message)
        return ChatResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="The AI provider could not complete the request. Please try again.",
        )
