from os.path import exists
from os import listdir

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from app.core.config import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_RETRIEVAL_K,
    DEFAULT_FETCH_K,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_SYSTEM_PROMPT,
)

from app.core.logger import get_logger


class RAGService:
    """
    Manages the complete Retrieval-Augmented Generation (RAG) workflow.

    Responsibilities:
        - Load or create the vector database
        - Configure semantic retrieval
        - Build the prompt template
        - Initialize the language model
        - Generate answers from retrieved context
    """

    def __init__(
        self,
        persist_directory: str = "chroma_db",
        prompt: str = DEFAULT_SYSTEM_PROMPT,
    ):
        self._logger = get_logger("rag_service")

        self._persist_directory = persist_directory
        self._embeddings = OpenAIEmbeddings()

        self._vector_store = None
        self._retriever = None

        self._prompt = ChatPromptTemplate.from_template(prompt)

        self._llm = ChatOpenAI(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMPERATURE,
        )

        self._rag_chain = None

    def initialize_from_file(self, file_path: str):
        """
        Build vector database from uploaded file.

        Currently supports PDF documents.
        Additional document loaders (TXT, DOCX, HTML, URLs)
        will be added in future phases.

        """

        self._logger.info(f"Initializing RAG from file: {file_path}")

        loader = PyPDFLoader(file_path)
        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        )

        chunked_docs = splitter.split_documents(documents)

        self._vector_store = Chroma.from_documents(
            documents=chunked_docs,
            embedding=self._embeddings,
            persist_directory=self._persist_directory,
        )

        self._retriever = self._vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": DEFAULT_RETRIEVAL_K,
                "fetch_k": DEFAULT_FETCH_K,
            },
        )

        self._rag_chain = self._build_chain()

        self._logger.info("RAG initialization complete")


    def answer_question(self, question: str) -> str:
        """
        Generate answer from RAG pipeline.
        """

        if not self._rag_chain:
            raise ValueError(
                "RAG system not initialized. Upload a document first."
            )

        return self._rag_chain.invoke(question)
    
