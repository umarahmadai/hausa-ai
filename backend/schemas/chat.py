from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Validated request schema for the chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message in Hausa or English (maximum 2,000 characters)",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("Message must not be blank.")
        return message


class ChatResponse(BaseModel):
    """Provider-neutral response schema for the chat endpoint."""

    response: str = Field(..., description="Assistant response")
    language: str = Field(
        default="auto",
        description="Detected language (hausa, english, or mixed)",
    )
