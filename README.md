# Neil's Playground

An experiment in building software with AI. Nearly all the code here is written by Claude — I provide direction, it writes the implementation.

**Setup:**
- Self-hosted on a 2012 Intel NUC (ESXi)
- Ubuntu VM for the application
- Separate Ubuntu VM for Kubernetes

[neiltoor.com](https://neiltoor.com/)

#-------

# Neil's Playground

A microservices-based AI playground with three main features: a RAG pipeline for comparing candidates, an inference interface for comparing LLM responses, and a natural language Kubernetes agent.

**Source Code:** [github.com/neiltoor/playground](https://github.com/neiltoor/playground)

## Features

### 1. RAG Pipeline - Candidate Comparison
Upload resumes and documents to ask AI-powered questions about candidates.

- Upload documents (PDF, TXT, DOCX, MD)
- Automatic document chunking and embedding
- Vector similarity search with pgvector
- Q&A powered by Claude or Grok

### 2. Inference Interface - LLM Comparison
Compare responses from different LLMs side-by-side in real-time.

- Side-by-side comparison of Claude (Anthropic) and Grok (xAI via OpenRouter)
- Send the same prompt to both LLMs simultaneously
- Compare responses and token usage
- See how different models interpret the same query

### 3. Activity Dashboard (Admin Only)
Monitor user activity and system usage.

- Login event tracking (success/failure)
- API call logging with timestamps and IP addresses
- Filter by username or activity type
- Real-time statistics (active users, total events)
- Role-based access control (admin only)

### 4. Kubectl Agent - Natural Language Kubernetes
Manage Kubernetes clusters using natural language commands.

- Chat-based interface powered by Claude
- Execute kubectl and helm commands via natural language
- Streaming responses with real-time progress
- Multi-turn conversations with context retention
- Fetch documentation and GitHub repos for helm installs

### General
- SSL/TLS support (HTTPS)
- JWT authentication with role-based access control
- Multiple LLM provider support (Anthropic + OpenRouter)
- Premium glassmorphism UI
- Everything runs locally with Docker Compose

## Tech Stack

- **Backend**: FastAPI (Python)
- **Vector Database**: PostgreSQL + pgvector
- **RAG Framework**: LlamaIndex
- **LLM Providers**: Anthropic (Claude), OpenRouter (Grok/xAI)
- **Frontend**: HTML/CSS/JavaScript (Vanilla)
- **Deployment**: Docker Compose (Microservices)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Nginx)                            │
│                    Port 8443 (HTTPS)                             │
│  login.html → landing.html → resume.html | llm-compare.html     │
│                              kubectl.html                        │
└─────────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┴────────────────────┐
          ▼                                         ▼
┌─────────────────────────────────┐  ┌─────────────────────────────┐
│        Backend (FastAPI)        │  │     Kubectl Agent           │
│          Port 8000              │  │       Port 8004             │
│  /api/login, /api/upload,       │  │  Natural language → kubectl │
│  /api/query, /api/llm-compare   │  │  Streaming chat interface   │
└─────────────────────────────────┘  └─────────────────────────────┘
          │                    │              │           │
          ▼                    ▼              ▼           ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────────────┐
│ Anthropic Service│  │ OpenRouter   │  │    Kubectl Service       │
│    Port 8001     │  │  Port 8002   │  │      Port 8003           │
│  Claude API      │  │  Grok/xAI    │  │  kubectl/helm executor   │
└──────────────────┘  └──────────────┘  └──────────────────────────┘
          │
          ▼
┌──────────────────┐
│   PostgreSQL     │
│   (pgvector)     │
└──────────────────┘
```

### Database Schema

```
PostgreSQL + pgvector extension

┌─────────────────────────────────────────────────────────────────┐
│                     document_embeddings                          │
│                   (Created by LlamaIndex)                        │
├─────────────────────────────────────────────────────────────────┤
│  id              UUID          PRIMARY KEY                       │
│  text            TEXT          Document chunk content            │
│  metadata_       JSONB         {document_id, filename, user_id}  │
│  node_id         VARCHAR       LlamaIndex node identifier        │
│  embedding       VECTOR(384)   all-MiniLM-L6-v2 embeddings       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        activity_log                              │
│                    (User Activity Tracking)                      │
├─────────────────────────────────────────────────────────────────┤
│  id              SERIAL        PRIMARY KEY                       │
│  username        VARCHAR(255)  User who performed action         │
│  activity_type   VARCHAR(50)   login | api_call                  │
│  resource_path   VARCHAR(500)  API endpoint accessed             │
│  ip_address      VARCHAR(45)   Client IP (IPv4/IPv6)             │
│  user_agent      TEXT          Browser/client info               │
│  timestamp       TIMESTAMP     When action occurred              │
│  details         TEXT          JSON with extra info              │
└─────────────────────────────────────────────────────────────────┘

Indexes:
  - idx_activity_log_username
  - idx_activity_log_timestamp
  - idx_activity_log_activity_type
```

## Prerequisites

- Docker and Docker Compose
- API Keys:
  - Anthropic API key ([Get one here](https://console.anthropic.com/))
  - OpenRouter API key ([Get one here](https://openrouter.ai/))

## Quick Start

### 1. Clone and navigate to the repository

```bash
cd the-pipeline
```

### 2. Set up configuration

Create `/data/config.json` with your API keys:

```json
{
  "llm_providers": {
    "anthropic": {
      "api_key": "sk-ant-..."
    },
    "openrouter": {
      "api_key": "sk-or-..."
    }
  }
}
```

Create `/data/auth` with login credentials (username:password:role format):

```
admin:your_password_here:admin
user1:password123:user
```

Roles:
- `admin` - Full access including Activity Dashboard
- `user` - Standard access (default if role omitted)

### 3. Start the application

```bash
docker-compose up --build
```

This will start:
- PostgreSQL with pgvector
- Anthropic LLM service
- OpenRouter LLM service
- Backend API server
- Nginx frontend server

### 4. Access the application

- **Web UI**: https://localhost:8443
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## User Flow

1. **Login** at https://localhost:8443
2. **Choose a tool** from the landing page:
   - **RAG Pipeline**: Upload resumes/documents and ask AI questions about candidates
   - **Inference Interface**: Compare Claude vs Grok responses side-by-side
   - **Activity Dashboard** (admin only): Monitor login events and API usage

## API Endpoints

### Authentication

```
POST /api/login
Content-Type: application/json

Body: { "username": "...", "password": "..." }
Response: { "access_token": "...", "token_type": "bearer", "username": "...", "role": "admin|user" }
```

```
GET /api/me
Authorization: Bearer <token>

Response: { "username": "...", "role": "..." }
```

### LLM Comparison

```
POST /api/llm-compare
Authorization: Bearer <token>
Content-Type: application/json

Body: {
  "prompt": "Your question here",
  "anthropic_model": "claude-3-haiku-20240307",
  "openrouter_model": "x-ai/grok-3-mini"
}

Response: {
  "prompt": "...",
  "anthropic": { "content": "...", "model": "...", "usage": {...} },
  "openrouter": { "content": "...", "model": "...", "usage": {...} }
}
```

### RAG Documents

```
POST /api/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

Response: {
  "document_id": "uuid",
  "filename": "example.pdf",
  "status": "success",
  "chunks_created": 15
}
```

```
GET /api/documents
Authorization: Bearer <token>

Response: [{ "id": "...", "filename": "...", "upload_date": "...", "chunk_count": 15 }]
```

```
POST /api/query
Authorization: Bearer <token>
Content-Type: application/json

Body: { "query": "What is...?", "top_k": 5, "provider": "anthropic" }
Response: { "answer": "...", "sources": [...], "query": "..." }
```

### Activity Monitoring (Admin Only)

```
GET /api/activity
Authorization: Bearer <admin_token>

Query params: limit, offset, username, activity_type
Response: {
  "logs": [{ "id": 1, "username": "...", "activity_type": "login|api_call", "resource_path": "...", "ip_address": "...", "timestamp": "...", "details": "..." }],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

```
GET /api/activity/stats
Authorization: Bearer <admin_token>

Response: { "by_type": {"login": 10, "api_call": 50}, "last_24_hours": 60, "unique_users_today": 3 }
```

### Health

```
GET /api/health

Response: { "status": "healthy", "database": "connected", "api_key_configured": true }
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `OPENROUTER_API_KEY` | - | OpenRouter API key |
| `POSTGRES_USER` | raguser | PostgreSQL username |
| `POSTGRES_PASSWORD` | ragpassword | PostgreSQL password |
| `POSTGRES_DB` | ragdb | PostgreSQL database name |
| `MAX_UPLOAD_SIZE` | 10485760 | Max file size in bytes (10MB) |
| `CHUNK_SIZE` | 512 | Tokens per chunk |
| `CHUNK_OVERLAP` | 50 | Token overlap between chunks |
| `TOP_K_RETRIEVAL` | 5 | Number of chunks to retrieve |
| `JWT_SECRET_KEY` | dev-secret-key | JWT signing key (change in production) |
| `JWT_EXPIRE_MINUTES` | 1440 | Token expiration (24 hours) |

### Config File

API keys can also be set in `/data/config.json`:

```json
{
  "llm_providers": {
    "anthropic": {
      "api_key": "sk-ant-...",
      "default_model": "claude-3-5-sonnet-20241022"
    },
    "openrouter": {
      "api_key": "sk-or-...",
      "default_model": "x-ai/grok-3-mini"
    }
  }
}
```

## Project Structure

```
the-pipeline/
├── docker-compose.yml              # Docker services orchestration
├── nginx.conf                      # Nginx configuration (SSL/HTTPS)
├── README.md
├── CLAUDE.md                       # AI assistant instructions
│
├── backend/                        # Main API server
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI application
│       ├── config.py               # Configuration management
│       ├── models.py               # Pydantic models
│       ├── database.py             # Database connection
│       ├── auth.py                 # JWT authentication + roles
│       ├── rag_engine.py           # LlamaIndex RAG logic
│       ├── api/
│       │   ├── auth.py             # Login endpoints
│       │   ├── upload.py           # Document upload (RAG)
│       │   ├── query.py            # RAG query
│       │   ├── llm_compare.py      # Inference interface endpoint
│       │   └── activity.py         # Activity monitoring (admin)
│       ├── services/
│       │   └── activity_service.py # Activity logging service
│       ├── middleware/
│       │   └── activity_logger.py  # Request logging middleware
│       └── tests/                  # Unit tests
│
├── services/                       # Microservices
│   ├── CLAUDE.md
│   ├── anthropic-service/          # Claude API wrapper (port 8001)
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── test_anthropic_service.py
│   ├── openrouter-service/         # Grok/xAI API wrapper (port 8002)
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── test_openrouter_service.py
│   ├── kubectl-service/            # kubectl/helm executor (port 8003)
│   │   ├── Dockerfile
│   │   └── main.py
│   └── kubectl-agent/              # Natural language K8s agent (port 8004)
│       ├── Dockerfile
│       ├── main.py                 # FastAPI endpoints
│       └── agent.py                # Agent orchestration logic
│
├── frontend/                       # Static web UI
│   ├── login.html                  # Login page
│   ├── landing.html                # Tool selection
│   ├── resume.html                 # RAG Pipeline interface
│   ├── llm-compare.html            # Inference Interface
│   ├── kubectl.html                # Kubectl Agent interface
│   ├── admin.html                  # Activity Dashboard (admin)
│   ├── css/
│   │   ├── styles.css              # Glassmorphism styling
│   │   └── admin.css               # Admin dashboard styles
│   └── js/
│       ├── login.js
│       ├── landing.js
│       ├── app.js                  # RAG tool logic
│       ├── llm-compare.js          # Inference interface logic
│       ├── kubectl.js              # Kubectl agent logic
│       └── admin.js                # Activity dashboard logic
│
├── ssl/                            # SSL certificates
│   └── .gitignore                  # Excludes private keys
│
├── db/
│   └── init.sql                    # PostgreSQL + pgvector init
│
├── tests/                          # Integration tests
│   ├── test_login_api.py
│   └── test_services_integration.py
│
└── docs/
    └── dependency-management.md
```

## Development

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f anthropic-service
docker-compose logs -f openrouter-service
```

### Restart services

```bash
docker-compose restart
docker-compose restart backend
```

### Rebuild after code changes

```bash
docker-compose up --build -d
```

### Run tests

```bash
docker-compose run --rm -v $(pwd)/tests:/app/tests backend pytest /app/tests/ -v
```

### Stop the application

```bash
docker-compose down
```

### Remove all data (including database)

```bash
docker-compose down -v
```

## Troubleshooting

### Services won't start

- Check API keys are configured in `/data/config.json`
- View logs: `docker-compose logs <service-name>`
- Ensure all health checks pass: `docker-compose ps`

### Authentication errors

- Verify `/data/auth` file exists with valid credentials
- Check JWT_SECRET_KEY matches across restarts
- Token expires after 24 hours - login again

### LLM Comparison shows errors

- Check both API keys are valid
- View service logs: `docker-compose logs anthropic-service openrouter-service`
- Verify services are healthy: `curl http://localhost:8000/api/health`

### RAG returns no results

- Ensure documents are uploaded successfully
- Check that chunks were created (see upload response)
- Try increasing `TOP_K_RETRIEVAL`

## License

MIT
