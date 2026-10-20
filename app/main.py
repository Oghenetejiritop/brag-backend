
"""BRAG FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_key_routes import router as api_key_router
from app.api.browser_auth_routes import router as browser_auth_router
from app.api.browser_chatbot_routes import router as browser_chatbot_router
from app.api.browser_knowledge_routes import router as browser_knowledge_router
from app.api.chatbot_exception_handlers import register_chatbot_exception_handlers
from app.api.chatbot_routes import router as chatbot_router
from app.api.routes import router
from app.api.security import SecurityHeadersMiddleware, register_unexpected_error_handler
from app.core.config import get_api_documentation_settings, get_cors_origins, validate_environment


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Validate settings before serving requests."""
    validate_environment()
    yield


app = FastAPI(
    title="BRAG API",
    description="Bot Retrieval-Augmented Generator Backend",
    version="0.1.0",
    lifespan=lifespan,
    **get_api_documentation_settings(),
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

for route in (
    router,
    api_key_router,
    chatbot_router,
    browser_auth_router,
    browser_chatbot_router,
    browser_knowledge_router,
):
    app.include_router(route)

register_chatbot_exception_handlers(app)
register_unexpected_error_handler(app)
