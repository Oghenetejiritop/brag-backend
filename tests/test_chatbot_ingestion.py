
"""Persistent multi-document ingestion, isolated for Windows Chroma cleanup."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent


def test_multiple_document_ingestion() -> None:
    # Native Chroma index handles may remain open until process termination.
    # A child process ensures handles close before TemporaryDirectory cleanup.
    with TemporaryDirectory() as directory:
        script = dedent('''
            import sys
            from langchain_core.documents import Document
            from langchain_core.embeddings import FakeEmbeddings
            from app.services.vector_store_service import VectorStoreService

            path = sys.argv[1]
            first = Document(page_content="BRAG supports private knowledge bases.",
                             metadata={"source": "first.txt"})
            second = Document(page_content="BRAG uses persistent Chroma vector stores.",
                              metadata={"source": "second.txt"})
            service = VectorStoreService(path, embeddings=FakeEmbeddings(size=32))
            first_store = service.add_documents([first])
            assert first_store._collection.count() == 1
            print("PASS: First document ingested.")
            second_store = service.add_documents([second])
            assert second_store._collection.count() == 2
            print("PASS: Second document appended.")
            reconstructed = VectorStoreService(path, embeddings=FakeEmbeddings(size=32))
            reopened = reconstructed.load_vector_store()
            assert reopened._collection.count() == 2
            stored = reopened._collection.get(include=["documents"])["documents"]
            assert first.page_content in stored
            assert second.page_content in stored
            print("PASS: Both documents survived reconstruction.")
        ''')
        result = subprocess.run(
            [sys.executable, "-c", script, str(Path(directory) / "chatbot_vectors")],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"Chroma ingestion subprocess failed ({result.returncode})\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        print(result.stdout, end="")
