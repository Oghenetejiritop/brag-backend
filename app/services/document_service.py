from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
)


class DocumentService:
    """
    Handles document loading and preprocessing for BRAG.

    Responsibilities:
        - Load supported document types.
        - Split documents into semantic chunks.

    This service intentionally does not perform embeddings,
    retrieval, or LLM interaction. Those responsibilities belong
    to RAGService.
    """

    def load_and_split(
        self,
        file_path: str,
    ) -> Document:
        """
        Load a document and split it into semantic chunks.

        Args:
            file_path:
                Path to the uploaded document.

        Returns:
            A list of LangChain Document chunks.
        """

        # Currently BRAG supports PDF ingestion.
        # Future versions will dynamically choose the appropriate
# loader based on the uploaded file extension.

        document_path = Path(file_path)

        loader = PyPDFLoader(str(document_path))

        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        )

        return splitter.split_documents(documents)