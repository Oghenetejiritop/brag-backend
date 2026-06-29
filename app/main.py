from fastapi import FastAPI

app = FastAPI(
    title="BRAG API",
    description="Bot Retrieval-Augmented Generator Backend",
    version="0.1.0",
)


@app.get("/")
def root():
    """
    Root endpoint to confirm the API is running.
    """

    return {
        "message": "Welcome to BRAG API"
    }


@app.get("/health")
def health():
    """
    Health check endpoint.

    Used by deployment platforms and monitoring tools
    to verify that the API is running.
    """

    return {
        "status": "healthy"
    }

