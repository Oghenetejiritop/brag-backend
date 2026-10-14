
"""
Public API response schemas for BRAG API-key management.

Never expose the stored key hash.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class APIKeyResponse(BaseModel):
    """Safe metadata describing an API key."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None

class APIKeyCreationResponse(BaseModel):
    """
    Response returned when a new API key is created.

    The plaintext credential is shown only once.
    """

    api_key_id: int
    key_prefix: str
    api_key: str
