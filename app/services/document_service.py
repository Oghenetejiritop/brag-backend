from pathlib import Path

from typing import (
    Any,
    Callable
    )

from langchain_community.document_loaders import (
    PyPDFLoader
    )

from langchain_core.documents import Document

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
    )

from app.core.config import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
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
    ) -> list[Document]:
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

        document_loader = self._select_loader(Path(file_path))
        documents = document_loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        )

        return splitter.split_documents(documents)

    def _select_loader(
        self,
        document_path: Path,
    ) -> Any:
        """
        Select the appropriate LangChain document loader.

        Currently BRAG supports PDF documents.

        Future versions will support additional loaders for
        TXT, DOCX, Markdown, HTML, and web pages without
        changing the document processing workflow.

        Args:
            document_path:
                Path to the uploaded document.

        Returns:
            A configured LangChain document loader.

        Raises:
            ValueError:
                If the document type is unsupported.
        """

        extension = document_path.suffix.lower()
        extension_loaders = self._get_supported_extension_loaders()

        if extension not in  extension_loaders:
            raise ValueError(
            f"Unsupported document type: {extension}"
        )

        return extension_loaders[extension](str(document_path))

    def _get_supported_extension_loaders(
            self
            ) -> dict[str, Callable]:
        """
        Retreive all BRAG supported extensions alongside their loaders
        """

        return {
            ".pdf": PyPDFLoader,
        }
    
