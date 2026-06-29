from os.path import exists
from os import listdir

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough


# =============================================================================
# Default Configuration
# These values centralize the RAG configuration and avoid hardcoded "magic
# numbers" throughout the codebase.
# =============================================================================

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150

DEFAULT_RETRIEVAL_K = 4
DEFAULT_FETCH_K = 20

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0


DEFAULT_SYSTEM_PROMPT = """
You are a helpful assistant that answers questions using only the provided context.

Instructions:
- Use only information from the retrieved context.
- If the user asks for a summary, overview, explanation, or description,
  summarize the retrieved context.
- If the answer is not present in the context, reply:
  "I don't know based on the provided information."
- Do not use outside knowledge or invent facts.

Context:
{context}

Question:
{question}
"""


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
        file: str,
        persist_directory: str = "chroma_db",
        prompt: str = DEFAULT_SYSTEM_PROMPT,
    ):
        self._file = file
        self._persist_directory = persist_directory

        self._embeddings = OpenAIEmbeddings()

        self._vector_store = self._initialize_vector_database()
        self._retriever = self._create_retriever()

        self._prompt = ChatPromptTemplate.from_template(prompt)

        self._llm = ChatOpenAI(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMPERATURE,
        )

        self._rag_chain = self._build_chain()

    def _initialize_vector_database(self):
        """
        Load an existing Chroma vector database if available.

        Otherwise, create a new vector database by loading,
        splitting, embedding, and storing the supplied document.
        """

        if (exists(self._persist_directory) and listdir(self._persist_directory)):
            print("[BRAG] Loading existing vector store...")

            return Chroma(
                persist_directory=self._persist_directory,
                embedding_function=self._embeddings,
            )

        print("[BRAG] Creating vector store...")

        loader = PyPDFLoader(self._file)
        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        )

        chunked_documents = splitter.split_documents(documents)

        return Chroma.from_documents(
            documents=chunked_documents,
            embedding=self._embeddings,
            persist_directory=self._persist_directory,
        )

    def _create_retriever(self):
        """
        Configure semantic retrieval using Maximum Marginal Relevance (MMR).

        MMR improves retrieval quality by returning relevant documents
        while reducing redundant results.
        """

        return self._vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": DEFAULT_RETRIEVAL_K,
                "fetch_k": DEFAULT_FETCH_K,
            },
        )

    def _build_chain(self):
        """
        Assemble the complete LCEL RAG pipeline.

            User Question

                    -> Semantic Retrieval
                    -> Format Documents
                    -> Prompt Template
                    -> Language Model
                    -> String Output Parser
        """

        return (
            {
                "context": self._retriever | self._format_documents,
                "question": RunnablePassthrough(),
            }
            | self._prompt
            | self._llm
            | StrOutputParser()
        )

    def _format_documents(self, documents: list) -> str:
        """
        Convert retrieved LangChain Document objects into a readable
        string for prompt injection.

        Including page numbers provides additional context for both
        users and future debugging.
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

    def answer_question(self, question: str) -> str:
        """
        Generate an answer using the configured RAG pipeline.

        Args:
            question: The user's natural language question.

        Returns:
            A response generated strictly from the retrieved context.
        """

        return self._rag_chain.invoke(question)