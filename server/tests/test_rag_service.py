"""Tests for RAG service."""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
from src.rag.rag_service import RAGService
from src.llm.llm_manager import LLMManager

@pytest.fixture
def test_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_vault_dir(test_dir):
    """Create a test vault directory with sample files."""
    vault_dir = Path(test_dir) / "test_vault"
    vault_dir.mkdir()
    
    # Create a sample markdown file
    with open(vault_dir / "test.md", "w") as f:
        f.write("# Test Document\n\nThis is a test document for RAG testing.")
    
    yield str(vault_dir)

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager."""
    mock = MagicMock(spec=LLMManager)
    mock.generate.return_value = "Test response"
    return mock

@pytest.fixture
def rag_service(tmp_path, mock_llm_manager):
    """Create RAG service instance for testing."""
    with patch('src.rag.rag_service.LLMManager', return_value=mock_llm_manager):
        service = RAGService(
            base_dir=str(tmp_path),
            llm_model_path="mock_model.gguf"
        )
        yield service

@pytest.mark.asyncio
async def test_vault_registration(rag_service, tmp_path):
    """Test vault registration."""
    # Create test vault
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    
    # Register vault
    vault_config = await rag_service.register_vault(
        name="test_vault",
        path=str(vault_path),
        file_types=["md"],
        enabled=True
    )
    
    assert vault_config["name"] == "test_vault"
    assert vault_config["path"] == str(vault_path)
    assert vault_config["file_types"] == ["md"]
    assert vault_config["enabled"] is True
    
    # Test duplicate registration
    with pytest.raises(ValueError):
        await rag_service.register_vault(
            name="test_vault",
            path=str(vault_path),
            file_types=["md"],
            enabled=True
        )

@pytest.mark.asyncio
async def test_file_processing(rag_service, tmp_path):
    """Test file processing."""
    # Create test vault and file
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    test_file = vault_path / "test.md"
    test_file.write_text("# Test\nThis is a test document.")
    
    # Register vault
    await rag_service.register_vault(
        name="test_vault",
        path=str(vault_path),
        file_types=["md"],
        enabled=True
    )
    
    # Process files
    stats = await rag_service.process_vault("test_vault")
    assert stats["processed_files"] == 1
    assert stats["total_files"] == 1
    assert stats["total_chunks"] > 0

@pytest.mark.asyncio
async def test_querying(rag_service, tmp_path):
    """Test querying functionality."""
    # Create test vault and file
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    test_file = vault_path / "test.md"
    test_file.write_text("# Test\nThis is a unique test document for querying.")
    
    # Register and process vault
    await rag_service.register_vault(
        name="test_vault",
        path=str(vault_path),
        file_types=["md"],
        enabled=True
    )
    await rag_service.process_vault("test_vault")
    
    # Test querying
    response = await rag_service.query("unique test document")
    assert response is not None
    assert isinstance(response, dict)
    assert "response" in response
    assert "sources" in response

@pytest.mark.asyncio
async def test_error_handling(rag_service):
    """Test error handling."""
    # Test querying without vaults
    with pytest.raises(ValueError, match="No vaults configured"):
        await rag_service.query("test query")
    
    # Test registering invalid vault path
    with pytest.raises(ValueError, match="Invalid vault path"):
        await rag_service.register_vault(
            name="invalid",
            path="/nonexistent/path",
            file_types=["md"],
            enabled=True
        )

@pytest.mark.asyncio
async def test_vault_management(rag_service, tmp_path):
    """Test vault management."""
    # Create test vault
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    
    # Register vault
    await rag_service.register_vault(
        name="test_vault",
        path=str(vault_path),
        file_types=["md"],
        enabled=True
    )
    
    # Test listing vaults
    vaults = await rag_service.list_vaults()
    assert len(vaults) == 1
    assert vaults[0]["name"] == "test_vault"
    
    # Test disabling vault
    await rag_service.disable_vault("test_vault")
    vaults = await rag_service.list_vaults()
    assert not any(v["enabled"] for v in vaults)
    
    # Test enabling vault
    await rag_service.enable_vault("test_vault")
    vaults = await rag_service.list_vaults()
    assert all(v["enabled"] for v in vaults)
    
    # Test removing vault
    await rag_service.remove_vault("test_vault")
    vaults = await rag_service.list_vaults()
    assert len(vaults) == 0 