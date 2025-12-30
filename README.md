# RAG Pipeline

A document Q&A application using Retrieval-Augmented Generation (RAG) with LlamaIndex, Claude API, and pgvector.

## Features

- Upload documents (PDF, TXT, DOCX, MD)
- Automatic document chunking and embedding
- Vector similarity search with pgvector
- Q&A powered by Claude AI
- Simple web UI for document management and queries
- Everything runs locally with Docker Compose

## Tech Stack

- **Backend**: FastAPI (Python)
- **Vector Database**: PostgreSQL + pgvector
- **RAG Framework**: LlamaIndex
- **LLM**: Claude API (Anthropic)
- **Frontend**: HTML/CSS/JavaScript
- **Deployment**: Docker Compose

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│   Frontend  │─────▶│   Backend   │─────▶│  PostgreSQL  │
│  (Nginx)    │      │  (FastAPI)  │      │  (pgvector)  │
│  Port 8080  │      │  Port 8000  │      │              │
└─────────────┘      └─────────────┘      └──────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Claude API │
                     │  (Anthropic)│
                     └─────────────┘
```

## Prerequisites

- Docker and Docker Compose
- Anthropic API key ([Get one here](https://console.anthropic.com/))

## Quick Start

### 1. Clone the repository

```bash
cd the-pipeline
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Start the application

```bash
docker-compose up --build
```

This will:
- Build the backend container
- Start PostgreSQL with pgvector
- Start the Nginx frontend server
- Initialize the RAG engine

### 4. Access the application

- **Web UI**: http://localhost:8080
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## Usage

### Upload Documents

1. Open http://localhost:8080 in your browser
2. Click "Browse Files" or drag and drop a document
3. Supported formats: PDF, TXT, DOCX, MD (max 10MB)
4. Wait for the document to be processed and chunked

### Ask Questions

1. Type your question in the chat input
2. Click "Send" or press Enter
3. The system will:
   - Retrieve relevant document chunks
   - Send context to Claude API
   - Display the answer with sources

## API Endpoints

### Health Check
```
GET /api/health
```

### Upload Document
```
POST /api/upload
Content-Type: multipart/form-data

Response:
{
  "document_id": "uuid",
  "filename": "example.pdf",
  "status": "success",
  "chunks_created": 15,
  "message": "..."
}
```

### Query Documents
```
POST /api/query
Content-Type: application/json

Body:
{
  "query": "What is the main topic?",
  "top_k": 5
}

Response:
{
  "answer": "The main topic is...",
  "sources": [...],
  "query": "What is the main topic?"
}
```

### List Documents
```
GET /api/documents

Response:
[
  {
    "id": "uuid",
    "filename": "example.pdf",
    "upload_date": "2025-01-01T00:00:00",
    "chunk_count": 15
  }
]
```

## Configuration

Environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | Your Anthropic API key (required) |
| `POSTGRES_USER` | raguser | PostgreSQL username |
| `POSTGRES_PASSWORD` | ragpassword | PostgreSQL password |
| `POSTGRES_DB` | ragdb | PostgreSQL database name |
| `MAX_UPLOAD_SIZE` | 10485760 | Max file size in bytes (10MB) |
| `CHUNK_SIZE` | 512 | Number of tokens per chunk |
| `CHUNK_OVERLAP` | 50 | Token overlap between chunks |
| `TOP_K_RETRIEVAL` | 5 | Number of chunks to retrieve |

## Project Structure

```
the-pipeline/
├── docker-compose.yml       # Docker services orchestration
├── .env                     # Environment variables (create from .env.example)
├── nginx.conf              # Nginx configuration
├── backend/
│   ├── Dockerfile          # Backend container definition
│   ├── requirements.txt    # Python dependencies
│   └── app/
│       ├── main.py         # FastAPI application
│       ├── config.py       # Configuration management
│       ├── models.py       # Pydantic models
│       ├── database.py     # Database connection
│       ├── rag_engine.py   # LlamaIndex RAG logic
│       └── api/
│           ├── upload.py   # Upload endpoints
│           └── query.py    # Query endpoints
├── frontend/
│   ├── index.html         # Main HTML page
│   ├── css/
│   │   └── styles.css     # Styling
│   └── js/
│       └── app.js         # Frontend logic
└── db/
    └── init.sql           # PostgreSQL initialization
```

## Development

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f frontend
```

### Restart services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
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

### Backend won't start

- Check that `ANTHROPIC_API_KEY` is set in `.env`
- View logs: `docker-compose logs backend`
- Ensure PostgreSQL is healthy: `docker-compose ps`

### Database connection errors

- Wait for PostgreSQL to fully start (health check)
- Check DATABASE_URL in `.env`
- View logs: `docker-compose logs postgres`

### Upload fails

- Check file size (max 10MB)
- Verify file type is supported (.pdf, .txt, .docx, .md)
- Check backend logs for errors

### Query returns no results

- Ensure documents are uploaded successfully
- Check that chunks were created (see upload response)
- Try increasing `TOP_K_RETRIEVAL` in `.env`

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
