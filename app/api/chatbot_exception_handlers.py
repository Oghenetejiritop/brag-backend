
"""
HTTP exception handlers for BRAG chatbot domain errors.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions.chatbot_exceptions import (
    ChatbotNotFoundError,
    InactiveChatbotError,
    InactiveChatbotOwnerError,
    InvalidChatbotNameError,
)


def register_chatbot_exception_handlers(app: FastAPI) -> None:
    """Register HTTP responses for chatbot domain exceptions."""

    @app.exception_handler(ChatbotNotFoundError)
    async def chatbot_not_found(
        request: Request,
        exc: ChatbotNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Chatbot was not found."},
        )

    @app.exception_handler(InactiveChatbotError)
    async def chatbot_inactive(
        request: Request,
        exc: InactiveChatbotError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Chatbot is inactive."},
        )

    @app.exception_handler(InactiveChatbotOwnerError)
    async def chatbot_owner_inactive(
        request: Request,
        exc: InactiveChatbotOwnerError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication is no longer valid."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(InvalidChatbotNameError)
    async def invalid_chatbot_name(
        request: Request,
        exc: InvalidChatbotNameError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Chatbot name is invalid."},
        )
