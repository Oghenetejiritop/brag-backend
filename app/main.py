
from fastapi import FastAPI

from app.api.routes import router
from app.api.chatbot_routes import router as chatbot_router



app = FastAPI(
    title="BRAG API",
    description="Bot Retrieval-Augmented Generator Backend",
    version="0.1.0",
)

# Existing legacy API endpoints.
app.include_router(router)

# Versioned persistent chatbot endpoints.
app.include_router(chatbot_router)
