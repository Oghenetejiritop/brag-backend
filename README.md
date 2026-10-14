# BRAG Backend

**BRAG (Bot Retrieval-Augmented Generator)** is a multi-user, API-first platform for creating custom AI-powered chatbots using Retrieval-Augmented Generation (RAG).

Users can create persistent chatbots, upload PDF documents, and query their knowledge bases through authenticated REST API endpoints.

BRAG is being developed as a backend-first Software-as-a-Service (SaaS) platform, with an accessible React frontend and deployment planned for upcoming development phases.

---

## Features

### Implemented

- **Persistent chatbot management:** Create, list, retrieve, and deactivate chatbots.
- **PDF document ingestion:** Upload PDF documents to chatbot-specific knowledge bases.
- **Retrieval-Augmented Generation:** Retrieve relevant document content and generate context-aware responses.
- **Semantic search:** Use embeddings and ChromaDB for document retrieval.
- **Multi-user architecture:** Associate chatbots, documents, and API keys with their respective owners.
- **API-key authentication:** Authenticate requests using Bearer tokens.
- **API-key management:** Create, list, and revoke API keys.
- **Tenant isolation:** Prevent users from accessing other users' chatbots and API keys.
- **Persistent storage:** Maintain chatbot records and knowledge bases across application restarts.
- **External API integration:** Query BRAG chatbots using Python or server-side JavaScript.
- **Automated security testing:** Verify authentication, key revocation, and user isolation.

### Planned

- Accessible React frontend
- Additional document formats: TXT and DOCX
- Web page ingestion
- Production deployment and configuration
- Usage monitoring and analytics
- Subscription and billing features

---

## Technology Stack

**Backend**
- Python
- FastAPI
- SQLAlchemy
- SQLite (development)

**AI and Retrieval**
- LangChain
- OpenAI API
- OpenAI Embeddings
- ChromaDB

**Testing and Integration**
- pytest
- FastAPI TestClient
- HTTPX
- Python Requests
- Node.js

**Frontend (Planned)**
- React
- Accessible, keyboard-first user interface

---

## How BRAG Works

1. A user authenticates using a BRAG API key.
2. The user creates a chatbot through the REST API.
3. The user uploads a PDF document to the chatbot.
4. BRAG processes the document, splits its content into chunks, and generates embeddings.
5. ChromaDB stores the embeddings for semantic retrieval.
6. The user sends a question to the chatbot.
7. BRAG retrieves relevant document content and uses an LLM to generate an answer.
8. The API returns the chatbot's response.

Each chatbot belongs to a specific user, and authenticated requests enforce ownership restrictions.

---

## Getting Started

### Prerequisites

- Python 3.12
- A valid OpenAI API key
- Git
- Node.js 18 or later (optional, for JavaScript integration)

### Clone the repository

```cmd
git clone https://github.com/Oghenetejiritop/brag-backend.git
cd brag-backend
```


### Create a virtual environment

On Windows Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### Install dependencies

```cmd
python -m pip install -r requirements.txt
```

### Configure environment variables

Configure the environment variables required by the application, including the OpenAI API key.

Never commit credentials or `.env` files containing secrets.

### Start the API

```cmd
uvicorn app.main:app --reload
```

Interactive API documentation:

http://127.0.0.1:8000/docs

---

## REST API

BRAG provides authenticated endpoints for managing chatbots, documents, and API keys.

### API-key management

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/api-keys` | List API keys |
| POST | `/api/v1/api-keys` | Create an API key |
| POST | `/api/v1/api-keys/{api_key_id}/revoke` | Revoke an API key |

### Chatbot management

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/chatbots` | Create a chatbot |
| GET | `/api/v1/chatbots` | List chatbots |
| GET | `/api/v1/chatbots/{chatbot_id}` | Retrieve a chatbot |
| PATCH | `/api/v1/chatbots/{chatbot_id}/deactivate` | Deactivate a chatbot |
| POST | `/api/v1/chatbots/{chatbot_id}/documents` | Upload a PDF |
| POST | `/api/v1/chatbots/{chatbot_id}/query` | Query a chatbot |

All endpoints listed above require authentication.

For endpoint details, request formats, and response examples, see the [REST API Guide](docs/api-guide.md).

---

## External Integration

BRAG chatbots can be accessed by external applications using authenticated HTTP requests.

### Python example

`tests/manual_chatbot_client.py`

### JavaScript example

`examples/javascript_chatbot_client.mjs`

The JavaScript example uses Node.js and should run in a trusted server-side environment.

**Security:** Never expose BRAG API keys in public frontend JavaScript or client-side React applications.

---

## Testing

Run the automated API security tests:

```cmd
python -m pytest tests/test_api_security.py -v
```

The security suite verifies:

- Missing credentials are rejected.
- Invalid credentials are rejected.
- Users cannot list another user's API keys.
- Users cannot revoke another user's API keys.
- Revoked credentials cannot authenticate.
- Users cannot access another user's chatbots.

Run all discovered tests:

```cmd
python -m pytest -v
```

---

## Project Roadmap

- **Phase 5:** Persistent backend, API authentication, chatbot management, document ingestion, external integration, and security tests.
- **Phase 6:** Backend hardening and production preparation.
- **Phase 7:** Accessible React frontend.
- **Phase 8:** Frontend/backend integration.
- **Phase 9:** Deployment.
- **Phase 10:** MVP testing and launch readiness.

Future enhancements include additional data sources, usage analytics, subscription management, and broader integration options.

---

## Project Goal

BRAG aims to make document-grounded AI chatbots accessible to individuals, developers, and businesses through a secure, reusable API.

The long-term vision is a scalable SaaS platform where users can manage their own knowledge bases and integrate custom chatbots into websites, applications, and business workflows.

---

## Author

**Oghenetejiri Peace Onosajerhe**

- [GitHub](https://github.com/oghenetejiritop)
- [LinkedIn](https://linkedin.com/in/oghenetejiritop)

---

## Project Status

**Active development — Backend MVP implementation and testing.**

The backend's core chatbot, document ingestion, authentication, and integration features are operational in the development environment. Production hardening, frontend development, and deployment remain in progress.

