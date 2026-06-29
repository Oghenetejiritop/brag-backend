from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """
    Request body for querying the RAG system.
    """

    question: str = Field(
        ...,
        min_length=1,
        description="The user's question."
    )


class QueryResponse(BaseModel):
    """
    Response returned by the RAG system.
    """

    answer: str