
"""
Domain exceptions for BRAG chatbot operations.

These exceptions represent application-level chatbot failures
without coupling the service layer to HTTP behavior.
"""


class ChatbotError(Exception):
    """
    Base exception for chatbot domain failures.
    """


class InvalidChatbotNameError(ChatbotError):
    """
    Raised when a chatbot name is missing or invalid.
    """


class ChatbotNotFoundError(ChatbotError):
    """
    Raised when a chatbot cannot be found for the current owner.
    """


class InactiveChatbotError(ChatbotError):
    """
    Raised when an operation requires an active chatbot.
    """


class InactiveChatbotOwnerError(ChatbotError):
    """
    Raised when an inactive user attempts a chatbot operation.
    """
    