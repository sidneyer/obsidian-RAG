"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import numpy as np
from src.main import app
from src.vault.vault_manager import VaultManager

@pytest.fixture
def mock_vault_manager():
    """Create mock vault manager."""
    mock = MagicMock(spec=VaultManager)
    
    # Mock search results
    mock.search.return_value = [
        {
            "content": "Test content",
            "similarity": 0.9,
            "source": "test.md"
        }
    ]
    
    # Mock vault listing with awaitable
    async def mock_list_vaults():
        return [
            {
                "name": "test_vault",
                "path": "/test/path",
                "file_types": ["md"],
                "enabled": True
            }
        ]
    mock.list_vaults = mock_list_vaults
    
    # Mock indexing stats
    mock.index_vault.return_value = {
        "processed_files": 10,
        "total_files": 10,
        "total_chunks": 50
    }
    
    return mock

@pytest.fixture
def client(mock_vault_manager):
    """Create test client."""
    # Override the vault manager dependency
    app.dependency_overrides[VaultManager] = lambda: mock_vault_manager
    client = TestClient(app)
    yield client
    # Clear dependency overrides after test
    app.dependency_overrides.clear()

@pytest.fixture
def mock_embeddings_manager():
    with patch('src.main.EmbeddingsManager') as mock:
        # Mock benchmark results
        mock.return_value.run_benchmark.return_value = {
            "platform": {
                "system": "Darwin",
                "machine": "arm64"
            },
            "compute_units": "NEURAL_ENGINE",
            "model_name": "all-MiniLM-L6-v2",
            "device": "mps",
            "benchmarks": {
                "batch_sizes": {1: 0.1, 4: 0.2, 8: 0.3},
                "optimal_batch_size": 4
            }
        }
        
        yield mock.return_value

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "version" in data
    assert "platform" in data

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_search(client, mock_vault_manager):
    """Test search endpoint."""
    # Mock successful search
    mock_vault_manager.search.return_value = [
        {
            "content": "Test content",
            "similarity": 0.9,
            "source": "test.md"
        }
    ]
    
    response = client.post(
        "/search",
        json={
            "query": "test query",
            "max_results": 5
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0

def test_index(client, mock_vault_manager):
    """Test index endpoint."""
    # Mock successful indexing
    mock_vault_manager.index_vault.return_value = {
        "processed_files": 10,
        "total_files": 10,
        "total_chunks": 50
    }
    
    response = client.post(
        "/index",
        params={"vault_name": "test_vault"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "stats" in data

def test_list_vaults(client, mock_vault_manager):
    """Test vault listing endpoint."""
    # Mock vault listing
    mock_vault_manager.list_vaults.return_value = [
        {
            "name": "test_vault",
            "path": "/test/path",
            "file_types": ["md"],
            "enabled": True
        }
    ]
    
    response = client.get("/vaults")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "name" in data[0]

def test_benchmark(client, mock_embeddings_manager):
    response = client.post("/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert "platform" in data
    assert "device" in data
    assert "optimal_batch_size" in data
    assert "results" in data

def test_error_handling(client, mock_vault_manager):
    """Test error handling."""
    # Test search error
    mock_vault_manager.search.side_effect = Exception("Search failed")
    response = client.post(
        "/search",
        json={
            "query": "test query",
            "max_results": 5
        }
    )
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data 