    
"""
Pydantic request and response schemas for BRAG chatbots.

Schemas define the public API contract without exposing
internal database identifiers or ORM implementation details.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatbotCreateRequest(BaseModel):
    """Validate the request for creating a chatbot."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable chatbot name.",
    )

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional chatbot description.",
    )


class ChatbotResponse(BaseModel):
    """Represent a chatbot in an API response."""

    model_config = ConfigDict(from_attributes=True)

    chatbot_id: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
