
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import (
    DEFAULT_FETCH_K,
    DEFAULT_RETRIEVAL_K,
    #DEFAULT_VECTOR_STORE_PATH
)


class VectorStoreService:
    """
    Handles vector database creation and retrieval configuration.

    Responsibilities:
        - Generate embeddings.
        - Build the Chroma vector store.
        - Configure semantic retrieval.
    """

    def __init__(
        self,
        persist_directory: str,
    ) -> None:
        """
        Initialize the vector store service.

        Args:
            persist_directory:
                Directory where the user's Chroma database
                will be stored.
        """

        self._persist_directory = str(persist_directory)

        # ---------------------------------------------------------
        # Shared embedding model used for vector generation.
        # ---------------------------------------------------------
        self._embeddings = OpenAIEmbeddings()

    def create_vector_store(
        self,
        documents: list[Document],
    ) -> Chroma:
        """
        Build a Chroma vector database from document chunks.

        Args:
            documents:
                Chunked LangChain documents.

        Returns:
            Configured Chroma vector database.
        """

        return Chroma.from_documents(
            documents=documents,
            embedding=self._embeddings,
            persist_directory=self._persist_directory,
        )

    def create_retriever(
        self,
        vector_store: Chroma,
    ):
        """
        Configure a Maximum Marginal Relevance (MMR) retriever.

        MMR balances relevance while reducing duplicate document
        chunks in the retrieval results.

        Args:
            vector_store:
                Initialized Chroma vector database.

        Returns:
            Configured LangChain retriever.
        """

        return vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": DEFAULT_RETRIEVAL_K,
                "fetch_k": DEFAULT_FETCH_K,
            },
        )
