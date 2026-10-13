
"""
Manual external-client integration test for BRAG.

Uses a BRAG API key to query an existing chatbot.

Requires:
    pip install requests

Credentials are read from environment variables.
"""

import os

import requests


API_BASE_URL = os.getenv(
    "BRAG_API_BASE_URL",
    "http://127.0.0.1:8000",
)


def main() -> None:
    """Query an existing BRAG chatbot over HTTP."""

    api_key = os.getenv("BRAG_API_KEY")
    chatbot_id = os.getenv("BRAG_CHATBOT_ID")

    if not api_key or not chatbot_id:
        raise RuntimeError(
            "Set BRAG_API_KEY and BRAG_CHATBOT_ID "
            "before running this test."
        )

    endpoint = (
        f"{API_BASE_URL}/api/v1/chatbots/"
        f"{chatbot_id}/query"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "question": (
            "What is the special test phrase "
            "in the uploaded document?"
        ),
    }

    response = requests.post(
        endpoint,
        headers=headers,
        json=payload,
        timeout=60,
    )

    print(f"HTTP status: {response.status_code}")

    response.raise_for_status()

    result = response.json()

    print(f"Chatbot ID: {result['chatbot_id']}")
    print(f"Answer: {result['answer']}")

    expected_phrase = (
        "The purple elephant plays Python chess."
    )

    assert expected_phrase in result["answer"], (
        "The expected document fact was not returned."
    )

    print("PASS: External BRAG API integration.")


if __name__ == "__main__":
    main()
