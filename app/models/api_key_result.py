
"""
Internal result model returned when BRAG creates an API key.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class APIKeyCreationResult:
    """
    Contains the newly issued API credential.

    The plaintext key is returned only at creation time and must
    never be persisted by BRAG.
    """

    api_key_id: int
    key_prefix: str
    api_key: str
