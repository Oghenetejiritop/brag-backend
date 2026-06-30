from os.path import exists

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma

from langchain_openai import (
    ChatOpenAI,
    OpenAIEmbeddings,
)

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

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
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_VECTOR_STORE_PATH,
    DEFAULT_FETCH_K,
    DEFAULT_MODEL,
    DEFAULT_RETRIEVAL_K,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
)

from app.core.logger import get_logger


class RAGService:
    """
    Handles the complete Retrieval-Augmented Generation (RAG) pipeline.

    Responsibilities
    ----------------
    - Load supported documents.
    - Split documents into semantic chunks.
    - Generate embeddings.
    - Build the Chroma vector database.
    - Configure semantic retrieval.
    - Execute the LangChain Expression Language (LCEL) pipeline.
    """

    def __init__(
        self,
        persist_directory: str = DEFAULT_VECTOR_STORE_PATH,
        prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:

        self._logger = get_logger("rag_service")

        self._persist_directory = persist_directory

        # -------------------------------------------------------------
        # OpenAI embedding model used for vector generation.
        # -------------------------------------------------------------
        self._embeddings = OpenAIEmbeddings()

        # -------------------------------------------------------------
        # These components are created only after a document upload.
        # -------------------------------------------------------------
        self._vector_store: Chroma | None = None
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

    def initialize_from_file(self, file_path: str) -> None:
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

        documents = self._load_documents(file_path)

        chunked_documents = self._split_documents(documents)

        self._create_vector_store(chunked_documents)

        self._create_retriever()

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

    def _load_documents(self, file_path: str) -> list:
        """
        Load documents from disk.

        Currently uses PyPDFLoader.

        Future loaders will be selected dynamically based on
        file extension.
        """

        loader = PyPDFLoader(file_path)

        return loader.load()

    def _split_documents(self, documents: list) -> list:
        """
        Split large documents into overlapping chunks.

        Chunk overlap helps preserve context between neighbouring
        chunks during retrieval.
        """

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        )

        return splitter.split_documents(documents)

    def _create_vector_store(
        self,
        chunked_documents: list,
    ) -> None:
        """
        Generate embeddings and store them inside Chroma.
        """

        self._vector_store = Chroma.from_documents(
            documents=chunked_documents,
            embedding=self._embeddings,
            persist_directory=self._persist_directory,
        )

    def _create_retriever(self) -> None:
        """
        Configure Maximum Marginal Relevance (MMR) retrieval.

        MMR reduces duplicate chunks while maintaining relevance.
        """

        if self._vector_store is None:
            raise ValueError(
                "Vector store has not been initialized."
            )

        self._retriever = self._vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": DEFAULT_RETRIEVAL_K,
                "fetch_k": DEFAULT_FETCH_K,
            },
        )

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