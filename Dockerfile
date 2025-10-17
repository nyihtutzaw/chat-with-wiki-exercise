FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy uv configuration
COPY pyproject.toml ./

# Install dependencies using uv pip
RUN uv pip install --system fastapi uvicorn[standard] chromadb pydantic python-multipart httpx beautifulsoup4 requests openai

# Copy application code
COPY app/ ./app/

# Create directory for ChromaDB persistence
RUN mkdir -p ./chroma_db

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
