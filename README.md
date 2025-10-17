# ChatWith Wiki - FastAPI + ChromaDB

A FastAPI application with ChromaDB vector database for document storage and semantic search, built with uv for Python environment management and Docker for containerization.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **React Frontend**: Beautiful chat interface with structured data rendering
- **ChromaDB**: Vector database for storing and searching documents
- **uv**: Fast Python package installer and resolver
- **Docker**: Containerized deployment
- **Semantic Search**: Query documents using natural language
- **LLM Integration**: OpenAI-powered query relevance filtering and response summarization
- **Smart Filtering**: Only searches when queries are relevant to Sai Sai Kham Leng
- **Auto-ingestion**: Automatically loads Wikipedia content on startup
- **Structured Data**: Tables and lists rendered beautifully in chat interface

## Demo Screenshots
<img width="1456" height="768" alt="Screenshot 2568-10-17 at 16 05 18" src="https://github.com/user-attachments/assets/a443f357-413d-4bec-8bcf-5ca1bfa1b521" />

<img width="1456" height="768" alt="Screenshot 2568-10-17 at 16 07 16" src="https://github.com/user-attachments/assets/7e9c1a8b-032c-4189-9887-8a9dda536c5f" />

<img width="1456" height="768" alt="Screenshot 2568-10-17 at 16 07 40" src="https://github.com/user-attachments/assets/9cf347d7-ee05-43d2-b7cd-aa2d56eddc2e" />

<img width="1456" height="768" alt="Screenshot 2568-10-17 at 16 06 08" src="https://github.com/user-attachments/assets/2bd17641-a362-4bda-a34a-b34cead220e5" />



## Project Structure

```
chatwith-wiki/
├── app/
│   ├── __init__.py
│   └── main.py              # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json         # Frontend dependencies
│   └── Dockerfile           # Frontend Docker config
├── pyproject.toml           # uv configuration and dependencies
├── Dockerfile               # Backend Docker configuration
├── docker-compose.yml       # Multi-service setup
├── .dockerignore
├── .gitignore
└── README.md
```

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `POST /documents/` - Add a new document
- `GET /documents/{document_id}` - Get document by ID
- `POST /search/` - Search documents semantically
- `DELETE /documents/{document_id}` - Delete document
- `GET /collection/info` - Get collection information

## Quick Start

### Using Docker (Recommended)

1. **Clone and navigate to the project:**
   ```bash
   cd chatwith-wiki
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   - **Frontend (Chat Interface)**: http://localhost:3000
   - **API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs
   - **ReDoc**: http://localhost:8000/redoc

### Local Development with uv

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the application:**
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Usage Examples

### Add a Document
```bash
curl -X POST "http://localhost:8000/documents/" \
     -H "Content-Type: application/json" \
     -d '{
       "id": "doc1",
       "content": "FastAPI is a modern, fast web framework for building APIs with Python.",
       "metadata": {"category": "technology", "author": "example"}
     }'
```

### Search Documents (with LLM filtering and summarization)
```bash
# Relevant query - will search and summarize
curl -X POST "http://localhost:8000/search/" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What movies did Sai Sai act in?",
       "n_results": 3
     }'

# Irrelevant query - will be filtered out
curl -X POST "http://localhost:8000/search/" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is the weather today?",
       "n_results": 3
     }'
```

### Get Document
```bash
curl -X GET "http://localhost:8000/documents/doc1"
```

### Collection Info
```bash
curl -X GET "http://localhost:8000/collection/info"
```

## Development

### Code Formatting
```bash
uv run black app/
uv run isort app/
```

### Linting
```bash
uv run flake8 app/
```

### Testing
```bash
uv run pytest
```

## Environment Variables

- `PYTHONPATH`: Set to `/app` in Docker
- ChromaDB data is persisted in `./chroma_db` directory

## Docker Commands

```bash
# Build the image
docker build -t chatwith-wiki .

# Run the container
docker run -p 8000:8000 -v $(pwd)/chroma_db:/app/chroma_db chatwith-wiki

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License
