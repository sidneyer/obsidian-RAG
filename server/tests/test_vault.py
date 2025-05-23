"""Tests for vault manager."""
import pytest
from pathlib import Path
import json
import numpy as np
from src.vault.vault_manager import VaultManager
from src.embeddings.embeddings_manager import EmbeddingsManager

@pytest.fixture
def vault_manager(tmp_path):
    """Create vault manager for testing."""
    config_dir = tmp_path / "config"
    return VaultManager(str(config_dir))

@pytest.fixture
def test_vault(tmp_path):
    """Create test vault directory."""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    return vault_path

@pytest.mark.asyncio
async def test_vault_configuration(vault_manager, test_vault):
    """Test vault configuration management."""
    # Test adding a vault
    vault_config = vault_manager.add_vault(
        name="test_vault",
        path=str(test_vault),
        file_types=["md"],
        enabled=True
    )
    
    assert vault_config["name"] == "test_vault"
    assert vault_config["path"] == str(test_vault)
    assert vault_config["file_types"] == ["md"]
    assert vault_config["enabled"] is True
    
    # Test getting vault
    retrieved_config = vault_manager.get_vault("test_vault")
    assert retrieved_config == vault_config
    
    # Test listing vaults
    vault_list = vault_manager.list_vaults()
    assert len(vault_list) == 1
    assert vault_list[0] == vault_config
    
    # Test disabling vault
    vault_manager.disable_vault("test_vault")
    assert not vault_manager.get_vault("test_vault")["enabled"]
    
    # Test enabling vault
    vault_manager.enable_vault("test_vault")
    assert vault_manager.get_vault("test_vault")["enabled"]
    
    # Test removing vault
    vault_manager.remove_vault("test_vault")
    assert vault_manager.get_vault("test_vault") is None

@pytest.mark.asyncio
async def test_vault_indexing(vault_manager, test_vault):
    """Test vault indexing."""
    # Create test files
    for i in range(3):
        file_path = test_vault / f"test{i}.md"
        file_path.write_text(f"# Test {i}\nThis is test content {i}")
    
    # Configure vault
    vault_manager.add_vault(
        name="test_vault",
        path=str(test_vault),
        file_types=["md"],
        enabled=True
    )
    
    # Test indexing
    stats = await vault_manager.index_vault("test_vault")
    assert stats["processed_files"] == 3
    assert stats["total_files"] == 3
    assert stats["total_chunks"] > 0  # At least one chunk per file
    
    # Verify index files were created
    index_dir = vault_manager.config_dir / "indices" / "test_vault"
    assert (index_dir / "embeddings.npy").exists()
    assert (index_dir / "chunks.json").exists()

@pytest.mark.asyncio
async def test_vault_search(vault_manager, test_vault):
    """Test vault search functionality."""
    # Create test file with specific content
    test_file = test_vault / "test.md"
    test_file.write_text("# Test\nThis is a unique test phrase for searching.")
    
    # Configure and index vault
    vault_manager.add_vault(
        name="test_vault",
        path=str(test_vault),
        file_types=["md"],
        enabled=True
    )
    await vault_manager.index_vault("test_vault")
    
    # Test search
    results = await vault_manager.search("unique test phrase")
    assert len(results) > 0
    assert all("similarity" in r for r in results)
    assert all("content" in r for r in results)
    assert all("vault" in r for r in results)

@pytest.mark.asyncio
async def test_error_handling(vault_manager):
    """Test error handling."""
    # Test invalid vault name
    with pytest.raises(ValueError):
        await vault_manager.index_vault("nonexistent")
    
    # Test invalid vault path
    with pytest.raises(ValueError):
        vault_manager.add_vault(
            name="invalid",
            path="/nonexistent/path",
            file_types=["md"],
            enabled=True
        )
    
    # Test duplicate vault name
    vault_manager.add_vault(
        name="test",
        path=str(Path.cwd()),
        file_types=["md"],
        enabled=True
    )
    with pytest.raises(ValueError):
        vault_manager.add_vault(
            name="test",
            path=str(Path.cwd()),
            file_types=["md"],
            enabled=True
        )

def test_file_watching(vault_manager, test_vault):
    """Test file watching functionality."""
    # Add vault
    vault_manager.add_vault(
        name="test_vault",
        path=str(test_vault),
        file_types=["md"],
        enabled=True
    )
    
    # Verify observer was created
    assert "test_vault" in vault_manager.observers
    assert vault_manager.observers["test_vault"].is_alive()
    
    # Test disabling stops observer
    vault_manager.disable_vault("test_vault")
    assert "test_vault" not in vault_manager.observers
    
    # Test enabling starts observer
    vault_manager.enable_vault("test_vault")
    assert "test_vault" in vault_manager.observers
    assert vault_manager.observers["test_vault"].is_alive()
    
    # Test removing vault stops observer
    vault_manager.remove_vault("test_vault")
    assert "test_vault" not in vault_manager.observers 