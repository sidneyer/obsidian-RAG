"""Tests for embeddings management."""
import pytest
import torch
import numpy as np
import platform
import os
from unittest.mock import MagicMock, patch
from src.embeddings import EmbeddingsManager

@pytest.fixture
def mock_sentence_transformer(monkeypatch):
    """Mock SentenceTransformer for testing."""
    mock = MagicMock()
    mock.encode.return_value = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
    
    class MockSentenceTransformer:
        def __init__(self, *args, **kwargs):
            self.encode = mock.encode
    
    monkeypatch.setattr("sentence_transformers.SentenceTransformer", MockSentenceTransformer)
    return mock

@pytest.fixture
def embeddings_manager(mock_sentence_transformer):
    """Create an embeddings manager for testing."""
    with patch("platform.system", return_value="Linux"), \
         patch("torch.cuda.is_available", return_value=False):
        return EmbeddingsManager()

def test_init():
    """Test initialization of embeddings manager."""
    with patch("platform.system", return_value="Linux"), \
         patch("torch.cuda.is_available", return_value=False):
        manager = EmbeddingsManager()
        assert manager.model_name == "all-MiniLM-L6-v2"  # Default model
        assert isinstance(manager.device, torch.device)
        assert str(manager.device) == "cpu"

def test_device_selection():
    """Test device selection logic."""
    with patch("platform.system") as mock_system, \
         patch("platform.machine") as mock_machine, \
         patch("torch.cuda.is_available") as mock_cuda:
        
        # Test MPS (Apple Silicon)
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"
        mock_cuda.return_value = False
        manager = EmbeddingsManager()
        assert str(manager.device) == "mps"
        
        # Test CPU fallback
        mock_system.return_value = "Linux"
        mock_cuda.return_value = False
        manager = EmbeddingsManager()
        assert str(manager.device) == "cpu"

@pytest.mark.asyncio
async def test_get_embeddings(embeddings_manager):
    """Test embedding generation."""
    texts = ["test text 1", "test text 2"]
    embeddings = await embeddings_manager.get_embeddings(texts)
    
    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (2, 2)  # Mock returns 2D embeddings
    
    # Check normalization
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, 1.0)

@pytest.mark.asyncio
async def test_empty_input(embeddings_manager):
    """Test handling of empty input."""
    with pytest.raises(ValueError, match="Empty input"):
        await embeddings_manager.get_embeddings([])

@pytest.mark.asyncio
async def test_error_handling(embeddings_manager, mock_sentence_transformer):
    """Test error handling during embedding generation."""
    mock_sentence_transformer.encode.side_effect = RuntimeError("Mock error")
    
    with pytest.raises(RuntimeError, match="Mock error"):
        await embeddings_manager.get_embeddings(["test"])

@pytest.mark.asyncio
async def test_neural_engine_optimization(monkeypatch):
    """Test Neural Engine optimization."""
    # Mock CoreML conversion
    mock_convert = MagicMock()
    mock_convert.return_value.save = MagicMock()
    monkeypatch.setattr("coremltools.convert", mock_convert)
    
    # Mock platform checks
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr("platform.machine", lambda: "arm64")
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    
    manager = EmbeddingsManager()
    assert manager.use_neural_engine is True
    
    # Verify CoreML model creation was attempted
    mock_convert.assert_called_once()

@pytest.mark.asyncio
async def test_benchmark(embeddings_manager):
    """Test benchmarking functionality."""
    results = await embeddings_manager.run_benchmark()
    
    assert "platform" in results
    assert "compute_units" in results
    assert "model_name" in results
    assert "device" in results
    assert "benchmarks" in results
    
    benchmarks = results["benchmarks"]
    assert "batch_sizes" in benchmarks
    assert "optimal_batch_size" in benchmarks
    
    # Verify platform info
    platform_info = results["platform"]
    assert platform_info["system"] == platform.system()
    assert platform_info["machine"] == platform.machine()
    assert platform_info["python_version"] == platform.python_version()
    assert platform_info["torch_version"] == torch.__version__ 