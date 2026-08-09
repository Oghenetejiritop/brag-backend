
from dataclasses import dataclass


@dataclass(frozen=True)
class UserContext:
    """
    Represents the authenticated BRAG user for a request.

    The user_id is the public UUID resolved after successful
    API-key authentication.

    Services use this context instead of accessing credentials
    or HTTP headers directly.
    """

    user_id: str
