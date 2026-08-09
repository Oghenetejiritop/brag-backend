"""
Domain-specific authentication exceptions for BRAG.

These exceptions keep authentication business logic independent
of FastAPI and HTTP response handling.
"""


class AuthenticationError(Exception):
    """
    Base exception for BRAG authentication failures.
    """


class InvalidAPIKeyError(AuthenticationError):
    """
    Raised when an API key cannot be authenticated.
    """


class InactiveAPIKeyError(AuthenticationError):
    """
    Raised when an API key exists but has been revoked.
    """


class InactiveUserError(AuthenticationError):
    """
    Raised when the API-key owner is inactive.
    """
