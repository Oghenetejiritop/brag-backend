from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
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
        embeddings: Embeddings | None = None,
    ) -> None:
        """
        Initialize the vector-store service.

        Args:
            persist_directory:
                Directory for persistent Chroma storage.
            embeddings:
                Optional embedding implementation. Defaults
                to OpenAI embeddings in production.
        """
        self._persist_directory = str(persist_directory)

        self._embeddings = (
            embeddings
            if embeddings is not None
            else OpenAIEmbeddings()
        )

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

    def load_vector_store(self) -> Chroma:
        """
        Load an existing persistent Chroma vector store.

        The method refuses to initialize a missing or empty
        database. This prevents an uninitialized chatbot from
        appearing ready after an application restart.

        Returns:
            Chroma:
                Existing vector store containing document chunks.

        Raises:
            FileNotFoundError:
                If no persisted Chroma database exists.

            ValueError:
                If the persisted collection contains no documents.

        Notes:
            Existing document embeddings are reused. Loading
            does not reprocess or re-embed source documents.
        """
        persist_path = Path(self._persist_directory)

        database_file = persist_path / "chroma.sqlite3"

        # Opening a missing Chroma directory could create a new,
        # empty database. Reject it before constructing Chroma.
        if not database_file.is_file():
            raise FileNotFoundError(
                "No persisted Chroma database was found "
                f"at: {persist_path}"
            )

        vector_store = Chroma(
            persist_directory=self._persist_directory,
            embedding_function=self._embeddings,
        )

        # An existing database file does not necessarily mean
        # the expected collection contains document vectors.
        if vector_store._collection.count() == 0:
            raise ValueError(
                "The persisted Chroma collection is empty."
            )

        return vector_store


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
