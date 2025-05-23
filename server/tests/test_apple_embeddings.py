"""Tests for Apple-specific embeddings manager."""
import pytest
import numpy as np
import platform
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
import json
import torch
import coremltools as ct
from src.embeddings.apple_embeddings import AppleEmbeddingsManager

@pytest.fixture
def mock_tokenizer():
    """Mock tokenizer for testing."""
    mock = MagicMock()
    mock.return_value = {
        "input_ids": np.array([[1, 2, 3]]),
        "attention_mask": np.array([[1, 1, 1]]),
        "token_type_ids": np.array([[0, 0, 0]])
    }
    return mock

@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer for testing."""
    mock = MagicMock()
    mock.encode.return_value = np.array([[1.0, 0.0], [0.0, 1.0]])
    mock.get_config_dict.return_value = {
        "modules": [{"model_name": "bert-base-uncased"}]
    }
    mock.get_model_name.return_value = "test-model"
    return mock

@pytest.fixture
def mock_coreml_model():
    """Mock CoreML model for testing."""
    mock = MagicMock()
    mock.predict.return_value = {"output": np.array([[1.0, 0.0]])}
    return mock

@pytest.fixture
def embeddings_manager(tmp_path, mock_sentence_transformer, mock_tokenizer, mock_coreml_model):
    """Create an Apple embeddings manager for testing."""
    with patch("platform.system", return_value="Darwin"), \
         patch("platform.processor", return_value="arm"), \
         patch("sentence_transformers.SentenceTransformer", return_value=mock_sentence_transformer), \
         patch("transformers.AutoTokenizer.from_pretrained", return_value=mock_tokenizer), \
         patch("coremltools.models.MLModel", return_value=mock_coreml_model):
        
        manager = AppleEmbeddingsManager(
            model_name="test-model",
            cache_dir=str(tmp_path),
            compute_units="ALL"
        )
        return manager

def test_init():
    """Test initialization."""
    with patch("platform.system", return_value="Darwin"), \
         patch("platform.processor", return_value="arm"):
        manager = AppleEmbeddingsManager()
        assert manager.model_name == "all-MiniLM-L6-v2"
        assert manager.compute_units == "ALL"
        assert manager.max_length == 384

def test_init_non_apple():
    """Test initialization on non-Apple hardware."""
    with patch("platform.system", return_value="Linux"):
        manager = AppleEmbeddingsManager()
        assert manager.coreml_model is None
        assert manager.tokenizer is None

def test_setup_tokenizer(embeddings_manager, mock_tokenizer):
    """Test tokenizer setup."""
    assert embeddings_manager.tokenizer is not None
    
    # Test error handling
    with patch("transformers.AutoTokenizer.from_pretrained", side_effect=Exception("Mock error")):
        manager = AppleEmbeddingsManager()
        assert manager.tokenizer is None

def test_preprocess_text(embeddings_manager):
    """Test text preprocessing."""
    inputs = embeddings_manager._preprocess_text("test text")
    assert "input_ids" in inputs
    assert "attention_mask" in inputs
    assert "token_type_ids" in inputs
    
    # Test error handling
    embeddings_manager.tokenizer = None
    with pytest.raises(RuntimeError):
        embeddings_manager._preprocess_text("test text")

@pytest.mark.asyncio
async def test_get_embeddings(embeddings_manager):
    """Test getting embeddings."""
    texts = ["test text 1", "test text 2"]
    embeddings = await embeddings_manager.get_embeddings(texts)
    
    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (2, 2)  # Mock returns 2D embeddings
    
    # Check normalization
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, 1.0)

@pytest.mark.asyncio
async def test_get_embeddings_coreml(embeddings_manager, mock_coreml_model):
    """Test getting embeddings with CoreML model."""
    texts = ["test text"]
    embeddings = await embeddings_manager.get_embeddings(texts)
    
    assert isinstance(embeddings, np.ndarray)
    mock_coreml_model.predict.assert_called_once()

def test_model_caching(tmp_path):
    """Test CoreML model caching."""
    with patch("platform.system", return_value="Darwin"), \
         patch("platform.processor", return_value="arm"):
        
        # First initialization should create model
        manager1 = AppleEmbeddingsManager(cache_dir=str(tmp_path))
        model_path = manager1._get_model_path()
        assert model_path.exists()
        
        # Metadata should be saved
        metadata_path = model_path.with_suffix(".json")
        assert metadata_path.exists()
        
        with open(metadata_path) as f:
            metadata = json.load(f)
            assert metadata["compute_units"] == "ALL"
            assert metadata["max_length"] == 384
        
        # Second initialization should load existing model
        with patch("coremltools.models.MLModel") as mock_load:
            manager2 = AppleEmbeddingsManager(cache_dir=str(tmp_path))
            mock_load.assert_called_once_with(str(model_path))

@pytest.mark.asyncio
async def test_search(embeddings_manager):
    """Test searching with embeddings."""
    query = "test query"
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
    texts = ["text 1", "text 2"]
    
    results = await embeddings_manager.search(query, embeddings, texts)
    
    assert len(results) > 0
    assert "text" in results[0]
    assert "similarity" in results[0]
    assert isinstance(results[0]["similarity"], float) 