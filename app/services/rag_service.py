
from os.path import exists
from pathlib import Path
import re
from collections import defaultdict

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError
)

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.core.config import (
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    CHATBOT_SYSTEM_MESSAGE,
    CHATBOT_MAX_CONTEXT_CHARS,
    CHATBOT_MAX_STORED_SCAN_CHUNKS,
)
from app.core.logger import get_logger
from app.exceptions.rag_exceptions import RAGProviderUnavailableError
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


    def initialize_chatbot_from_file(
        self,
        file_path: str,
        user_id: str,
        chatbot_id: str,
    ) -> None:
        """
        Ingest a document into one chatbot's persistent knowledge base.

        Existing document chunks are preserved.
        """
        if not exists(file_path):
            raise FileNotFoundError(
                f"Document not found: {file_path}"
            )

        self._logger.info(
            "Ingesting document for chatbot '%s'",
            chatbot_id,
        )

        documents = self._document_service.load_and_split(
            file_path
        )

        if not documents:
            raise ValueError(
                "The uploaded document contains no usable content."
            )

        vector_store_directory = (
            self._workspace_service
            .get_chatbot_vector_store_directory(
                user_id=user_id,
                chatbot_id=chatbot_id,
            )
        )

        vector_store_service = VectorStoreService(
            persist_directory=str(vector_store_directory),
        )

        vector_store = vector_store_service.add_documents(
            documents
        )

        retriever = vector_store_service.create_retriever(
            vector_store
        )

        self._vector_store = vector_store
        self._retriever = retriever

        try:
            self._rag_chain = self._build_chain()

        except Exception:
            self._vector_store = None
            self._retriever = None
            self._rag_chain = None
            raise

        self._logger.info(
            "Document ingestion completed for chatbot '%s'",
            chatbot_id,
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
        *,
        assistant_name: str | None = None,
        assistant_description: str | None = None,
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

        try:
            if assistant_name is None:
                # Preserve the legacy authenticated user-level RAG endpoint.
                return self._rag_chain.invoke(question)

            if self._retriever is None:
                raise ValueError("Retriever has not been initialized.")
            # Retrieve from the already-authorized assistant's vector store.
            # Blend semantic results with bounded lexical and page-spread
            # evidence. No extra LLM classifier, no filename/page requirement.
            documents = self._retriever.invoke(question)
            context = self._build_chatbot_context(question, documents)
            return self._generate_grounded_answer(
                question=question,
                context=context,
                assistant_name=assistant_name,
                assistant_description=assistant_description,
            )
        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as error:
            self._logger.warning(
                "AI provider request failed: %s", type(error).__name__
            )
            raise RAGProviderUnavailableError(
                "The AI service is temporarily unavailable."
            ) from error

    @staticmethod
    def _terms(value: str) -> set[str]:
        """Meaningful lexical tokens; semantic retriever remains primary."""
        stop = {"what", "which", "where", "when", "who", "how", "about",
                "your", "you", "does", "have", "from", "with", "that", "this",
                "tell", "more", "please", "could", "would", "information",
                "document", "documents", "uploaded", "knowledge", "summarize",
                "summary", "explain", "give", "based", "the", "and", "for"}
        return {t for t in re.findall(r"[a-z0-9]+", value.lower())
                if len(t) > 2 and t not in stop}

    def _build_chatbot_context(self, question: str, semantic_documents: list) -> str:
        """Select bounded, diverse evidence within this assistant's collection.

        MMR finds semantic matches; lexical overlap helps proper names; page
        spread helps broad questions. No cross-assistant database is queried.
        """
        candidates = []
        seen = set()

        def add(text, metadata):
            if not text or not text.strip():
                return
            metadata = metadata or {}
            key = (str(metadata.get("source", "")), metadata.get("page"), text)
            if key not in seen:
                seen.add(key)
                candidates.append((text, metadata))

        for doc in semantic_documents:
            add(doc.page_content, doc.metadata)

        if self._vector_store is not None:
            collection = self._vector_store._collection
            # Never scan indefinitely on a very large knowledge base.
            total = min(collection.count(), CHATBOT_MAX_STORED_SCAN_CHUNKS)
            stored = []
            for offset in range(0, total, 200):
                batch = collection.get(
                    limit=min(200, total-offset), offset=offset,
                    include=["documents", "metadatas"],
                )
                for text, meta in zip(batch.get("documents") or [],
                                      batch.get("metadatas") or []):
                    if text and text.strip():
                        stored.append((text, meta or {}))

            terms = self._terms(question)
            if terms:
                ranked = sorted(stored,
                    key=lambda pair: len(terms & self._terms(pair[0])),
                    reverse=True)
                for text, meta in ranked[:6]:
                    if terms & self._terms(text):
                        add(text, meta)

            # Spread a few samples across each source. This is supplemental,
            # not a guarantee of exhaustive long-document summarization.
            by_source = defaultdict(list)
            for text, meta in stored:
                by_source[str(meta.get("source", "Unknown"))].append((text, meta))
            for group in by_source.values():
                group.sort(key=lambda item: (
                    int(item[1].get("page", 0) or 0),
                    int(item[1].get("start_index", 0) or 0)))
                for index in sorted({0, len(group)//2, len(group)-1}):
                    text, meta = group[index]
                    add(text, meta)

        output = []
        used = 0
        for text, meta in candidates:
            page = meta.get("page")
            page_label = str(page + 1) if isinstance(page, int) else "unknown"
            name = Path(str(meta.get("source") or "Unknown document")).name
            entry = f"Source: {name}; page: {page_label}\n{text}"
            if used + len(entry) > CHATBOT_MAX_CONTEXT_CHARS:
                continue
            output.append(entry)
            used += len(entry)
        return "\n\n---\n\n".join(output)

    def _generate_grounded_answer(
        self, *, question: str, context: str,
        assistant_name: str, assistant_description: str | None,
    ) -> str:
        """Keep identity separate from untrusted uploaded content."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", CHATBOT_SYSTEM_MESSAGE),
            ("human", "Relevant excerpts from this assistant's PDFs:\n"
                      "{context}\n\nUser question: {question}"),
        ])
        return (prompt | self._llm | StrOutputParser()).invoke({
            "assistant_name": assistant_name,
            "assistant_description": assistant_description or "No description provided.",
            "context": context,
            "question": question,
        })

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
