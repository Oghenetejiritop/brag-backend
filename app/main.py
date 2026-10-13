
from fastapi import FastAPI

from app.api.chatbot_exception_handlers import (
    register_chatbot_exception_handlers,
)

from app.api.routes import router
from app.api.api_key_routes import router as api_key_router
from app.api.chatbot_routes import router as chatbot_router



app = FastAPI(
    title="BRAG API",
    description="Bot Retrieval-Augmented Generator Backend",
    version="0.1.0",
)

routers = [
    router,    # Existing legacy API endpoints.
    api_key_router,    # Authenticated API-key management endpoints.
    chatbot_router,    # Versioned persistent chatbot endpoints.
]

for route in routers:
    app.include_router(route)

register_chatbot_exception_handlers(app)
