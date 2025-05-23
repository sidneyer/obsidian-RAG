"""Tests for configuration management."""
import pytest
import os
import json
import platform
from pathlib import Path
from src.config import Config, EmbeddingsConfig, ChunkingConfig, CacheConfig, SystemConfig

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_path = tmp_path / "config.json"
    config_data = {
        "embeddings": {
            "model_name": "test-model",
            "cache_dir": str(tmp_path / "cache"),
            "force_cpu": True,
            "compute_units": "CPU_ONLY",
            "batch_size": 16
        },
        "chunking": {
            "chunk_size": 256,
            "chunk_overlap": 32,
            "preserve_markdown": False
        },
        "cache": {
            "embeddings_cache": True,
            "models_cache": True,
            "max_cache_size_mb": 512,
            "cache_cleanup_interval": 1800
        },
        "system": {
            "debug": True,
            "log_level": "DEBUG",
            "max_concurrent_requests": 5,
            "timeout_seconds": 15
        }
    }
    config_path.write_text(json.dumps(config_data))
    return config_path

def test_default_config():
    """Test default configuration creation."""
    config = Config()
    
    assert isinstance(config.embeddings, EmbeddingsConfig)
    assert isinstance(config.chunking, ChunkingConfig)
    assert isinstance(config.cache, CacheConfig)
    assert isinstance(config.system, SystemConfig)
    
    # Check default values
    assert config.embeddings.model_name == "all-MiniLM-L6-v2"
    assert config.chunking.chunk_size == 500
    assert config.cache.max_cache_size_mb == 1024
    assert config.system.log_level == "INFO"

def test_load_config(temp_config_file):
    """Test loading configuration from file."""
    config = Config.load(str(temp_config_file))
    
    assert config.embeddings.model_name == "test-model"
    assert config.embeddings.force_cpu is True
    assert config.chunking.chunk_size == 256
    assert config.chunking.preserve_markdown is False
    assert config.cache.max_cache_size_mb == 512
    assert config.system.debug is True

def test_save_config(tmp_path):
    """Test saving configuration to file."""
    config = Config()
    config.embeddings.model_name = "custom-model"
    config.system.debug = True
    
    config_path = str(tmp_path / "saved_config.json")
    config.save(config_path)
    
    # Load and verify
    loaded_config = Config.load(config_path)
    assert loaded_config.embeddings.model_name == "custom-model"
    assert loaded_config.system.debug is True

def test_platform_specific_defaults():
    """Test platform-specific default configuration."""
    config = Config.load()
    
    if platform.system() == "Darwin" and platform.processor() == "arm":
        assert config.embeddings.compute_units == "ALL"
        assert config.embeddings.batch_size == 16
        assert config.cache.max_cache_size_mb == 2048
    elif platform.system() == "Linux":
        assert config.embeddings.batch_size == 64
        assert config.system.max_concurrent_requests == 20

def test_update_from_benchmark():
    """Test updating configuration from benchmark results."""
    config = Config()
    benchmark_results = {
        "model_name": "benchmark-model",
        "batch_size": 24,
        "compute_units": "CPU_AND_NE",
        "expected_memory_mb": 1024
    }
    
    config.update_from_benchmark(benchmark_results)
    
    assert config.embeddings.model_name == "benchmark-model"
    assert config.embeddings.batch_size == 24
    assert config.embeddings.compute_units == "CPU_AND_NE"
    assert config.cache.max_cache_size_mb == 2048  # 2x expected memory

def test_invalid_config_file():
    """Test handling of invalid configuration file."""
    config = Config.load("nonexistent_file.json")
    assert isinstance(config, Config)  # Should return default config
    
    # Test corrupted JSON
    with open("corrupted.json", "w") as f:
        f.write("invalid json content")
    
    config = Config.load("corrupted.json")
    assert isinstance(config, Config)  # Should return default config
    
    # Cleanup
    os.remove("corrupted.json")

def test_validate_resources(monkeypatch):
    """Test resource validation."""
    class MockVirtualMemory:
        def __init__(self, available):
            self.available = available
    
    class MockPsutil:
        @staticmethod
        def virtual_memory():
            # Mock 4GB available
            return MockVirtualMemory(4 * 1024 * 1024 * 1024)
    
    monkeypatch.setattr("psutil.virtual_memory", MockPsutil.virtual_memory)
    
    config = Config()
    config.cache.max_cache_size_mb = 2048  # 2GB cache
    config.embeddings.batch_size = 16
    
    # Should pass with 4GB available
    assert config.validate_resources() is True
    
    # Should fail with large cache size
    config.cache.max_cache_size_mb = 8192  # 8GB cache
    assert config.validate_resources() is False 