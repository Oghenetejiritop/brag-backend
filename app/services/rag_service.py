from os.path import exists

from langchain_openai import ChatOpenAI

from langchain_core.output_parsers import (
    StrOutputParser,
)

from langchain_core.prompts import (
    ChatPromptTemplate,
)

from langchain_core.runnables import (
    RunnablePassthrough,
)

from app.core.config import (
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
)

from app.core.logger import get_logger

from app.services.document_service import DocumentService
from app.services.workspace_service import WorkspaceService
from app.services.vector_store_service import VectorStoreService


class RAGService:
    """
    Handles the complete Retrieval-Augmented Generation (RAG) pipeline.

    Responsibilities

    ----------------
    - Coordinate the RAG pipeline.
    - Generate embeddings.
    - Build the vector database.
    - Configure semantic retrieval.
    - Build the LCEL chain.
    - Answer user questions.
    """

    def __init__(
        self,
        prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:

        self._logger = get_logger("rag_service")

        # -------------------------------------------------------------
        # Responsible for resolving user-specific workspace paths.
        # -------------------------------------------------------------
        self._workspace_service = WorkspaceService()

        # -------------------------------------------------------------
        # Service responsible for document loading and preprocessing.
        # -------------------------------------------------------------
        self._document_service = DocumentService()

        
        # -------------------------------------------------------------
        # Created after a document has been uploaded.
        # -------------------------------------------------------------
        self._vector_store = None
        self._retriever = None
        self._rag_chain = None

        self._prompt = ChatPromptTemplate.from_template(prompt)

        self._llm = ChatOpenAI(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMPERATURE,
        )

    # ================================================================
    # Public Methods
    # ================================================================

    def initialize_from_file(
            self,
            file_path: str,
            user_id: str,
            ) -> None:
        """
        Initialize the complete RAG pipeline from a document.

        During Phase 3 BRAG supports PDF documents.

        Future phases will add:
            - TXT
            - DOCX
            - HTML
            - Web URLs
        """

        if not exists(file_path):
            raise FileNotFoundError(
                f"Document not found: {file_path}"
            )

        self._logger.info(f"Initializing RAG from '{file_path}'")

        chunked_documents =self._document_service.load_and_split(
            file_path
            )

        # -------------------------------------------------------------
        # Resolve the vector store location for the active user.
        # Each user owns an independent Chroma database.
        # -------------------------------------------------------------
        vector_store_directory = (
            self._workspace_service.get_vector_store_directory(str(
                user_id
            )
            )
        )

        # -------------------------------------------------------------
        # Create a vector store service configured for the active user.
        # -------------------------------------------------------------
        vector_store_service = VectorStoreService(
            persist_directory=vector_store_directory,
        )

        # Delegate vector database creation to the dedicated service.

        self._vector_store = (
            vector_store_service.create_vector_store(
                chunked_documents
                )
                )

        # Configure semantic retrieval.
        self._retriever = (
            vector_store_service.create_retriever(
                self._vector_store
                )
                )

        self._rag_chain = self._build_chain()

        self._logger.info("RAG initialization completed successfully.")

    def answer_question(self, question: str) -> str:
        """
        Execute the RAG pipeline using the supplied question.
        """

        if self._rag_chain is None:
            raise ValueError(
                "RAG system has not been initialized. "
                "Upload a document first."
            )

        return self._rag_chain.invoke(question)

    # ================================================================
    # Private Helper Methods
    # ================================================================

    def _format_documents(
        self,
        documents: list,
    ) -> str:
        """
        Convert LangChain Document objects into a readable prompt.

        Including page numbers improves explainability and debugging.
        """

        formatted_documents = []

        for document in documents:

            page = document.metadata.get("page", "Unknown")

            if isinstance(page, int):
                page += 1

            formatted_documents.append(
                f"Page {page}\n"
                "--------------------\n"
                f"{document.page_content}"
            )

        return "\n\n".join(formatted_documents)

    def _build_chain(self):
        """
        Construct the complete LCEL RAG pipeline.

        Pipeline

        User Question
        - Retriever
        - Document Formatter
        - Prompt
        LLM
        - Output Parser
        """

        if self._retriever is None:
            raise ValueError(
                "Retriever has not been initialized."
            )

        return (
            {
                "context": self._retriever | self._format_documents,
                "question": RunnablePassthrough(),
            }
            | self._prompt
            | self._llm
            | StrOutputParser()
        )
    