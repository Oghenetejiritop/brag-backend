
"""
End-to-end persistence test across separate Python processes.

Using subprocesses ensures Chroma file handles are closed
before Windows removes the temporary database.
"""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run_worker(action: str, directory: Path) -> None:
    """Run a worker and fail if it exits unsuccessfully."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.rag_restart_worker",
            action,
            str(directory),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )

    if result.stdout:
        print(result.stdout, end="")

    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    if result.returncode != 0:
        raise AssertionError(
            f"Restart worker '{action}' failed "
            f"with exit code {result.returncode}."
        )


def test_rag_restart() -> None:
    """Verify Chroma persistence across process boundaries."""
    with TemporaryDirectory() as temporary_directory:
        vector_directory = (
            Path(temporary_directory)
            / "chatbot_vector_store"
        )

        run_worker("create", vector_directory)
        run_worker("restore", vector_directory)

    print("PASS: Temporary Chroma files cleaned up.")
    print("PASS: RAG restart test completed.")


if __name__ == "__main__":
    test_rag_restart()
