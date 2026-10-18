
"""Request and response schemas for BRAG browser authentication."""

from pydantic import (
    BaseModel,
    Field
)


class CredentialsRequest(BaseModel):
    """Email and password supplied for registration or login."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class AccountResponse(BaseModel):
    """Public account information without private credentials."""

    user_id: str
    email: str


class SessionResponse(AccountResponse):
    """Account information and a CSRF token for browser requests."""

    csrf_token: str
