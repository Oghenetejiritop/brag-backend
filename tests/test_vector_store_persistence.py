
"""Chroma persistence regression test with process-scoped native handles."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent


def test_vector_store_persistence() -> None:
    with TemporaryDirectory() as directory:
        script = dedent('''
            import sys
            from pathlib import Path
            from langchain_core.documents import Document
            from langchain_core.embeddings import Embeddings
            from app.services.vector_store_service import VectorStoreService

            class FakeEmbeddings(Embeddings):
                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    return [self._embed_text(text) for text in texts]

                def embed_query(self, text: str) -> list[float]:
                    return self._embed_text(text)

                @staticmethod
                def _embed_text(text: str) -> list[float]:
                    return [float(len(text) + 1),
                            float(sum(ord(char) for char in text) % 997 + 1),
                            float(sum(char.isalpha() for char in text) + 1), 1.0]

            root = Path(sys.argv[1])
            path = root / "chatbot_vector_store"
            documents = [Document(
                page_content="BRAG is a retrieval augmented generation platform.",
                metadata={"source": "test_document"},
            )]
            creator = VectorStoreService(str(path), embeddings=FakeEmbeddings())
            created = creator.create_vector_store(documents)
            assert created._collection.count() == 1
            print("PASS: Persistent Chroma database created.")

            loader = VectorStoreService(str(path), embeddings=FakeEmbeddings())
            reopened = loader.load_vector_store()
            assert reopened._collection.count() == 1
            print("PASS: Existing Chroma database reopened.")
            results = reopened.similarity_search("What is BRAG?", k=1)
            assert len(results) == 1
            assert "BRAG" in results[0].page_content
            print("PASS: Persisted document content retrieved.")

            missing = root / "missing_vector_store"
            missing_loader = VectorStoreService(str(missing), embeddings=FakeEmbeddings())
            try:
                missing_loader.load_vector_store()
            except FileNotFoundError:
                pass
            else:
                raise AssertionError("Missing Chroma database was accepted.")
            assert not missing.exists()
            print("PASS: Missing vector database rejected.")
        ''')
        result = subprocess.run(
            [sys.executable, "-c", script, str(Path(directory))],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"Chroma persistence subprocess failed ({result.returncode})\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        print(result.stdout, end="")
