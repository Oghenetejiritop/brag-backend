
from os.path import exists

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.core.config import (
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
)
from app.core.logger import get_logger
from app.services.document_service import DocumentService
from app.services.vector_store_service import VectorStoreService
from app.services.workspace_service import WorkspaceService


class RAGService:
    """
    Coordinate BRAG's Retrieval-Augmented Generation pipeline.

    Responsibilities:
        - Load and preprocess documents.
        - Create user-specific vector stores.
        - Configure semantic retrieval.
        - Build the LCEL RAG chain.
        - Answer questions using retrieved context.
    """

    def __init__(
        self,
        prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        """
        Initialize the RAG service.

        Args:
            prompt:
                System prompt template used by the RAG chain.
        """

        self._logger = get_logger("rag_service")

        self._workspace_service = WorkspaceService()
        self._document_service = DocumentService()

        # These resources are created after a document is loaded.
        self._vector_store = None
        self._retriever = None
        self._rag_chain = None

        self._prompt = ChatPromptTemplate.from_template(
            prompt
        )

        self._llm = ChatOpenAI(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMPERATURE,
        )

    def initialize_from_file(
        self,
        file_path: str,
        user_id: str,
    ) -> None:
        """
        Initialize the RAG pipeline from an uploaded document.

        Args:
            file_path:
                Path to the authenticated user's document.

            user_id:
                Persistent public UUID of the authenticated user.

        Raises:
            FileNotFoundError:
                If the supplied document does not exist.
        """

        if not exists(file_path):
            raise FileNotFoundError(
                f"Document not found: {file_path}"
            )

        self._logger.info(
            "Initializing RAG from '%s'",
            file_path,
        )

        chunked_documents = (
            self._document_service.load_and_split(
                file_path
            )
        )

        vector_store_directory = (
            self._workspace_service
            .get_vector_store_directory(
                user_id
            )
        )

        vector_store_service = VectorStoreService(
            persist_directory=vector_store_directory,
        )

        self._vector_store = (
            vector_store_service.create_vector_store(
                chunked_documents
            )
        )

        self._retriever = (
            vector_store_service.create_retriever(
                self._vector_store
            )
        )

        self._rag_chain = self._build_chain()

        self._logger.info(
            "RAG initialization completed successfully."
        )

    def initialize_from_existing_store(
        self,
        user_id: str,
        chatbot_id: str,
    ) -> None:
        """
        Reconstruct a chatbot's RAG pipeline from persisted vectors.

        The caller must have already verified that the chatbot
        belongs to the authenticated user and is active.

        Existing document embeddings are reused rather than
        regenerated.

        Args:
            user_id:
                Public UUID of the authenticated chatbot owner.
            chatbot_id:
                Public UUID of the chatbot to reconstruct.

        Raises:
            FileNotFoundError:
                If the chatbot has no persisted vector database.
            ValueError:
                If the existing vector collection is empty.
        """
        vector_store_directory = (
            self._workspace_service
            .get_chatbot_vector_store_directory(
                user_id=user_id,
                chatbot_id=chatbot_id,
            )
        )

        self._logger.info(
            "Reconstructing RAG for chatbot '%s'",
            chatbot_id,
        )

        vector_store_service = VectorStoreService(
            persist_directory=str(vector_store_directory),
        )

        # Load existing vectors without reprocessing documents.
        vector_store = vector_store_service.load_vector_store()

        # Build the new retriever before updating instance state.
        retriever = vector_store_service.create_retriever(
            vector_store
        )

        self._vector_store = vector_store
        self._retriever = retriever

        try:
            self._rag_chain = self._build_chain()
        except Exception:
            # Never leave a partially initialized pipeline
            # available after reconstruction fails.
            self._vector_store = None
            self._retriever = None
            self._rag_chain = None
            raise

        self._logger.info(
            "RAG reconstruction completed for chatbot '%s'",
            chatbot_id,
        )

    def answer_question(
        self,
        question: str,
    ) -> str:
        """
        Answer a question using the initialized RAG pipeline.

        Raises:
            ValueError:
                If the RAG pipeline has not been initialized.
        """

        if self._rag_chain is None:
            raise ValueError(
                "RAG system has not been initialized. "
                "Upload a document first."
            )

        return self._rag_chain.invoke(
            question
        )

    def _format_documents(
        self,
        documents: list,
    ) -> str:
        """
        Convert retrieved documents into prompt-ready context.

        Page information is retained when available to improve
        traceability of generated answers.
        """

        formatted_documents = []

        for document in documents:
            page = document.metadata.get(
                "page",
                "Unknown",
            )

            if isinstance(page, int):
                page += 1

            formatted_documents.append(
                f"Page {page}\n"
                "--------------------\n"
                f"{document.page_content}"
            )

        return "\n\n".join(
            formatted_documents
        )

    def _build_chain(self):
        """
        Build the LangChain Expression Language RAG pipeline.

        Raises:
            ValueError:
                If a retriever has not been initialized.
        """

        if self._retriever is None:
            raise ValueError(
                "Retriever has not been initialized."
            )

        return (
            {
                "context": (
                    self._retriever
                    | self._format_documents
                ),
                "question": RunnablePassthrough(),
            }
            | self._prompt
            | self._llm
            | StrOutputParser()
        )
