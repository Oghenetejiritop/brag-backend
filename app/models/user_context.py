from dataclasses import dataclass


@dataclass(frozen=True)
class UserContext:
    """
    Represents the active user making a request.

    During Phase 4, BRAG uses a temporary user identifier
    supplied through the X-User-ID request header.

    Future phases will replace this identifier with API-key
    authentication while keeping the remainder of the
    application unchanged.
    """

    user_id: str

