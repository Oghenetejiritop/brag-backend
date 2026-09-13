
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import (
    DEFAULT_FETCH_K,
    DEFAULT_RETRIEVAL_K,
)


class VectorStoreService:
    """
    Manage vector-store creation and retrieval configuration.

    Responsibilities:
        - Generate document embeddings.
        - Create persistent Chroma vector stores.
        - Configure semantic retrieval.
    """

    def __init__(
        self,
        persist_directory: str,
    ) -> None:
        """
        Initialize the vector-store service.

        Args:
            persist_directory:
                Directory where the user's Chroma database
                will be persisted.
        """

        # Chroma expects the persistence location as a string.
        self._persist_directory = str(
            persist_directory
        )

        self._embeddings = OpenAIEmbeddings()

    def create_vector_store(
        self,
        documents: list[Document],
    ) -> Chroma:
        """
        Create a persistent Chroma vector store.

        Args:
            documents:
                Preprocessed LangChain document chunks.

        Returns:
            Initialized Chroma vector store.
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
        Create an MMR retriever for a vector store.

        Maximum Marginal Relevance balances relevance with
        diversity to reduce repetitive retrieved chunks.

        Args:
            vector_store:
                Initialized Chroma vector store.

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
