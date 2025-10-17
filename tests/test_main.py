import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to ChatWith Wiki API"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"

def test_add_and_get_document():
    # Add a document
    document_data = {
        "id": "test_doc_1",
        "content": "This is a test document for FastAPI and ChromaDB integration.",
        "metadata": {"category": "test", "author": "pytest"}
    }
    
    response = client.post("/documents/", json=document_data)
    assert response.status_code == 200
    assert "added successfully" in response.json()["message"]
    
    # Get the document
    response = client.get(f"/documents/{document_data['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == document_data["id"]
    assert response.json()["content"] == document_data["content"]

def test_search_documents():
    # First add a document
    document_data = {
        "id": "search_test_doc",
        "content": "FastAPI is a modern web framework for building APIs with Python.",
        "metadata": {"category": "technology"}
    }
    
    client.post("/documents/", json=document_data)
    
    # Search for the document
    search_data = {
        "query": "web framework Python",
        "n_results": 5
    }
    
    response = client.post("/search/", json=search_data)
    assert response.status_code == 200
    assert "documents" in response.json()
    assert len(response.json()["documents"]) > 0

def test_collection_info():
    response = client.get("/collection/info")
    assert response.status_code == 200
    assert "collection_name" in response.json()
    assert "document_count" in response.json()
