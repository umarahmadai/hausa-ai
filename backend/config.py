from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Explicit origins only. Add the deployed frontend origin in Render.
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Per-process best-effort protection for the public chat endpoint.
    API_RATE_LIMIT_REQUESTS: int = Field(default=30, ge=1, le=1000)
    API_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1, le=3600)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_allowed_origins(cls, value: str) -> str:
        origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must contain at least one explicit origin.")

        for origin in origins:
            if origin == "*" or "://" not in origin:
                raise ValueError("Wildcard or invalid CORS origins are not allowed.")
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(f"Invalid CORS origin: {origin}")

        return ",".join(origins)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
