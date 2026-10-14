
# BRAG REST API Guide

BRAG (Bot Retrieval-Augmented Generator) lets developers
create document-grounded chatbots and query them through
an authenticated REST API.

## 1. Development server

Start the backend from the project root:

    uvicorn app.main:app --reload

Local API base URL:

    http://127.0.0.1:8000

Interactive API documentation:

    http://127.0.0.1:8000/docs

## 2. Authentication

Protected endpoints require a BRAG API key.

Send the key in the HTTP Authorization header:

    Authorization: Bearer YOUR_BRAG_API_KEY

Keep API keys secret. Do not commit them to Git or
embed them in public frontend JavaScript.

A missing, invalid, or revoked key returns HTTP 401.

## 3. API-key management

All endpoints below require authentication.

GET /api/v1/api-keys
    List the authenticated user's API-key metadata.

POST /api/v1/api-keys
    Create another API key for the authenticated user.
    Returns HTTP 201 and the new plaintext key once.

POST /api/v1/api-keys/{api_key_id}/revoke
    Revoke an API key belonging to the authenticated user.
    The revoked key can no longer authenticate.

API-key listing never returns complete credentials or
stored credential hashes.

## 4. Chatbot management

POST /api/v1/chatbots
    Create a chatbot.
    Request body:
    {
      "name": "My Knowledge Assistant",
      "description": "Answers questions about my documents"
    }

GET /api/v1/chatbots
    List chatbots owned by the authenticated user.

GET /api/v1/chatbots/{chatbot_id}
    Retrieve an owned, active chatbot.

PATCH /api/v1/chatbots/{chatbot_id}/deactivate
    Deactivate an owned chatbot.

## 5. Document upload

POST /api/v1/chatbots/{chatbot_id}/documents

Upload a PDF using multipart/form-data.

Form field:
    file

The chatbot must belong to the authenticated user
and must be active.

Current MVP upload support:
    PDF files, maximum 10 MiB.

## 6. Ask a question

POST /api/v1/chatbots/{chatbot_id}/query

Request body:
    {
      "question": "What does the uploaded document explain?"
    }

Successful response:
    {
      "chatbot_id": "YOUR_CHATBOT_ID",
      "answer": "An answer based on the uploaded document."
    }

The chatbot requires an initialized knowledge base.

## 7. Important HTTP responses

200: Successful retrieval, query, or revocation.
201: Resource created successfully.
401: Authentication missing or invalid.
404: Resource not found or not owned by the user.
409: Chatbot knowledge base not initialized.
422: Invalid request data or failed document ingestion.

## 8. Security and tenant isolation

- API keys belong to individual users.
- Chatbots belong to individual users.
- Users cannot list or revoke another user's API keys.
- Users cannot retrieve another user's chatbots.
- API keys are stored as hashes.
- Plaintext keys are returned only during creation.
- Revoked keys cannot authenticate.

## 9. Development notes

The current API is an MVP. Payment processing,
public chatbot widgets, advanced analytics, and
additional document formats are future enhancements.

Use HTTPS for deployed API requests.

Never place a BRAG API key directly in a public
React application or browser-accessible source code.
