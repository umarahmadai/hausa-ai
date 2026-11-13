import logging
import httpx
from google import genai
from google.genai import types

from backend.config import settings

logger = logging.getLogger(__name__)


class HausaAIService:
    """Gemini-first Hausa/English assistant with Groq fallback."""

    def __init__(self):
        self.gemini_client = (
            genai.Client(api_key=settings.GEMINI_API_KEY)
            if settings.GEMINI_API_KEY else None
        )

    @staticmethod
    def _get_system_prompt() -> str:
        return """You are HausaAI Pro, an intelligent and culturally aware assistant.
Reply in the language the user uses: Hausa for Hausa, English for English,
and natural code-switching when the user mixes both. Be accurate, respectful,
clear, practical, and concise when appropriate. Do not invent facts. If a
request is unclear, ask a focused clarification question. Help with learning,
translation, programming, technology, business, and everyday questions."""

    def _ask_gemini(self, message: str) -> str:
        response = self.gemini_client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=self._get_system_prompt(),
                temperature=0.7,
            ),
        )
        answer = getattr(response, "text", None)
        if not answer:
            raise RuntimeError("Gemini returned an empty response.")
        return answer.strip()

    def _ask_groq(self, message: str) -> str:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": message},
                ],
                "temperature": 0.7,
            },
            timeout=45.0,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
        if not answer:
            raise RuntimeError("Groq returned an empty response.")
        return answer.strip()

    def chat(self, message: str) -> dict:
        if not self.gemini_client and not settings.GROQ_API_KEY:
            raise RuntimeError("Add GEMINI_API_KEY or GROQ_API_KEY to the server environment.")

        if self.gemini_client:
            try:
                answer = self._ask_gemini(message)
                return {"response": answer, "language": self._detect_language(message)}
            except Exception:
                logger.exception("Gemini request failed; attempting Groq fallback.")

        if settings.GROQ_API_KEY:
            try:
                answer = self._ask_groq(message)
                return {"response": answer, "language": self._detect_language(message)}
            except Exception:
                logger.exception("Groq request failed.")

        raise RuntimeError("All configured AI providers are temporarily unavailable.")

    @staticmethod
    def _detect_language(text: str) -> str:
        hausa_words = {
            "sannu", "yaya", "kake", "kike", "ina", "ne", "ce", "yau",
            "gida", "gobe", "jiya", "wannan", "wadannan", "amma", "wallahi",
            "kai", "ni", "mu", "su", "zan", "ban", "gane", "lafiya",
            "nagode", "menene", "saboda", "kana", "kuna", "nake"
        }
        words = [w.strip(".,!?;:()[]{}\"'").lower() for w in text.split()]
        words = [w for w in words if w]
        if not words:
            return "english"
        ratio = sum(w in hausa_words for w in words) / len(words)
        if ratio >= 0.30:
            return "hausa"
        if ratio >= 0.10:
            return "mixed"
        return "english"
