from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="BRAG API",
    description="Bot Retrieval-Augmented Generator Backend",
    version="0.1.0",
)


app.include_router(router)