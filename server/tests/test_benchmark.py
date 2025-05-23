"""Tests for embeddings benchmark module."""
import pytest
import numpy as np
from pathlib import Path
import json
import psutil
from unittest.mock import MagicMock, patch
from src.embeddings.benchmark import EmbeddingsBenchmark, BenchmarkResult
from src.processors.chunking import Chunk

@pytest.fixture
def benchmark_result():
    """Create a sample benchmark result."""
    return BenchmarkResult(
        model_name="test-model",
        device="cpu",
        batch_size=8,
        num_samples=100,
        avg_latency_ms=10.0,
        throughput=1000.0,
        memory_mb=500.0,
        compute_units="ALL"
    )

@pytest.fixture
def temp_results_file(tmp_path):
    """Create a temporary results file."""
    results_file = tmp_path / "benchmark_results.json"
    sample_results = [
        {
            "model_name": "model1",
            "device": "cpu",
            "batch_size": 8,
            "num_samples": 100,
            "avg_latency_ms": 15.0,
            "throughput": 800.0,
            "memory_mb": 400.0,
            "compute_units": "ALL"
        }
    ]
    with open(results_file, "w") as f:
        json.dump(sample_results, f)
    return results_file

@pytest.fixture
def mock_embeddings_manager():
    """Create a mock embeddings manager."""
    mock = MagicMock()
    mock.device = "cpu"
    
    async def mock_get_embeddings(*args, **kwargs):
        return np.random.rand(10, 384), [{"source": f"test_{i}"} for i in range(10)]
    
    mock.get_embeddings = mock_get_embeddings
    return mock

def test_benchmark_result_conversion(benchmark_result):
    """Test BenchmarkResult conversion to/from dict."""
    # Test to_dict
    result_dict = benchmark_result.to_dict()
    assert result_dict["model_name"] == "test-model"
    assert result_dict["device"] == "cpu"
    assert result_dict["batch_size"] == 8
    assert result_dict["compute_units"] == "ALL"
    
    # Test from_dict
    new_result = BenchmarkResult.from_dict(result_dict)
    assert new_result.model_name == benchmark_result.model_name
    assert new_result.device == benchmark_result.device
    assert new_result.batch_size == benchmark_result.batch_size
    assert new_result.compute_units == benchmark_result.compute_units

def test_benchmark_initialization(temp_results_file):
    """Test benchmark initialization and results loading."""
    benchmark = EmbeddingsBenchmark(results_file=str(temp_results_file))
    assert len(benchmark.previous_results) == 1
    assert benchmark.previous_results[0].model_name == "model1"
    
    # Test initialization with non-existent file
    benchmark = EmbeddingsBenchmark(results_file="nonexistent.json")
    assert len(benchmark.previous_results) == 0

def test_generate_test_data():
    """Test test data generation."""
    benchmark = EmbeddingsBenchmark()
    chunks = benchmark.generate_test_data(
        num_samples=10,
        min_length=50,
        max_length=100
    )
    
    assert len(chunks) == 10
    assert all(isinstance(chunk, Chunk) for chunk in chunks)
    # Test content length (words * avg word length)
    assert all(50 <= len(chunk.content) <= 100 for chunk in chunks)
    assert all("benchmark" in chunk.content for chunk in chunks)
    assert all(chunk.metadata["type"] == "test" for chunk in chunks)
    # Test character positions
    assert all(chunk.start_char >= 0 for chunk in chunks)
    assert all(chunk.end_char > chunk.start_char for chunk in chunks)
    assert all(chunk.end_char == len(chunk.content) for chunk in chunks)

@pytest.mark.asyncio
async def test_run_benchmark(mock_embeddings_manager):
    """Test benchmark execution."""
    with patch("src.embeddings.benchmark.EmbeddingsManagerFactory.create", 
              return_value=mock_embeddings_manager):
        
        benchmark = EmbeddingsBenchmark()
        results = await benchmark.run_benchmark(
            model_name="test-model",
            batch_sizes=[1, 8],
            num_samples=10
        )
        
        assert len(results) == 2  # One result per batch size
        for result in results:
            assert result.model_name == "test-model"
            assert result.device == "cpu"
            assert result.num_samples == 10
            assert result.avg_latency_ms > 0
            assert result.throughput > 0
            assert result.memory_mb >= 0

def test_save_results(tmp_path, benchmark_result):
    """Test saving benchmark results."""
    results_file = tmp_path / "results.json"
    benchmark = EmbeddingsBenchmark(results_file=str(results_file))
    benchmark.previous_results = [benchmark_result]
    benchmark._save_results()
    
    assert results_file.exists()
    with open(results_file) as f:
        saved_data = json.load(f)
        assert len(saved_data) == 1
        assert saved_data[0]["model_name"] == "test-model"

def test_get_optimal_config(benchmark_result):
    """Test getting optimal configuration."""
    benchmark = EmbeddingsBenchmark()
    benchmark.previous_results = [
        benchmark_result,
        BenchmarkResult(
            model_name="test-model",
            device="cpu",
            batch_size=16,
            num_samples=100,
            avg_latency_ms=15.0,
            throughput=800.0,
            memory_mb=800.0,
            compute_units="ALL"
        )
    ]
    
    # Test with memory constraint
    optimal = benchmark.get_optimal_config(max_memory_mb=600.0)
    assert optimal["batch_size"] == 8  # Should choose first result due to memory constraint
    
    # Test with throughput constraint
    optimal = benchmark.get_optimal_config(min_throughput=900.0)
    assert optimal["batch_size"] == 8  # Should choose first result due to throughput requirement
    
    # Test with no constraints
    optimal = benchmark.get_optimal_config()
    assert optimal["batch_size"] in [8, 16]  # Should choose highest throughput config

@pytest.mark.asyncio
async def test_benchmark_error_handling():
    """Test error handling in benchmark."""
    with patch("src.embeddings.benchmark.EmbeddingsManagerFactory.create", 
              side_effect=Exception("Mock error")):
        
        benchmark = EmbeddingsBenchmark()
        results = await benchmark.run_benchmark(num_samples=1)
        assert len(results) == 0  # Should handle error gracefully

@pytest.mark.asyncio
async def test_memory_measurement():
    """Test memory measurement in benchmark."""
    benchmark = EmbeddingsBenchmark()
    
    # Create a memory intensive operation
    data = [0] * (10 * 1024 * 1024)  # Allocate ~10MB
    process = psutil.Process()
    before_mem = process.memory_info().rss / 1024 / 1024
    
    # Run benchmark with small sample
    results = await benchmark.run_benchmark(num_samples=1, batch_sizes=[1])
    
    # Memory should have increased
    assert len(results) == 1
    assert results[0].memory_mb > 0
    
    del data  # Cleanup 