"""Benchmarking utilities for embeddings performance."""
import time
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from .factory import EmbeddingsManagerFactory
from ..processors.chunking import Chunk

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    model_name: str
    device: str
    batch_size: int
    num_samples: int
    avg_latency_ms: float
    throughput: float  # tokens/second
    memory_mb: float
    compute_units: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "batch_size": self.batch_size,
            "num_samples": self.num_samples,
            "avg_latency_ms": self.avg_latency_ms,
            "throughput": self.throughput,
            "memory_mb": self.memory_mb,
            "compute_units": self.compute_units
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BenchmarkResult':
        """Create from dictionary."""
        return cls(**data)

class EmbeddingsBenchmark:
    """Benchmark different embedding configurations."""
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        results_file: Optional[str] = None
    ):
        """
        Initialize benchmarking.
        
        Args:
            cache_dir: Directory for caching models
            results_file: File to save benchmark results
        """
        self.cache_dir = cache_dir
        self.results_file = Path(results_file) if results_file else None
        self.previous_results: List[BenchmarkResult] = []
        
        if self.results_file and self.results_file.exists():
            self._load_previous_results()
    
    def _load_previous_results(self) -> None:
        """Load previous benchmark results."""
        try:
            with open(self.results_file) as f:
                data = json.load(f)
                self.previous_results = [
                    BenchmarkResult.from_dict(result) for result in data
                ]
        except Exception as e:
            logger.error(f"Error loading benchmark results: {str(e)}")
    
    def _save_results(self) -> None:
        """Save benchmark results."""
        if not self.results_file:
            return
            
        try:
            results_data = [result.to_dict() for result in self.previous_results]
            with open(self.results_file, 'w') as f:
                json.dump(results_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving benchmark results: {str(e)}")
    
    def generate_test_data(
        self,
        num_samples: int = 100,
        min_length: int = 50,
        max_length: int = 500
    ) -> List[Chunk]:
        """
        Generate test data for benchmarking.
        
        Args:
            num_samples: Number of test samples
            min_length: Minimum text length
            max_length: Maximum text length
            
        Returns:
            List of test chunks
        """
        chunks = []
        words = ['test', 'data', 'sample', 'text', 
                'embeddings', 'neural', 'network', 'machine', 'learning']
        
        # Generate varied length texts
        for i in range(num_samples):
            # Keep generating text until we meet the length requirements
            while True:
                # Calculate how many words we need based on average word length
                avg_word_len = sum(len(word) for word in words) / len(words)
                target_words = int(np.random.randint(min_length, max_length) / (avg_word_len + 1))  # +1 for space
                
                # Always include 'benchmark' as the first word
                selected_words = ['benchmark'] + list(np.random.choice(words, size=target_words-1))
                np.random.shuffle(selected_words)  # Randomize word order
                
                text = ' '.join(selected_words)
                if min_length <= len(text) <= max_length:
                    break
            
            chunks.append(Chunk(
                content=text,
                metadata={
                    'source': f'benchmark_{i}',
                    'type': 'test'
                },
                start_char=0,
                end_char=len(text)
            ))
        
        return chunks
    
    async def run_benchmark(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        batch_sizes: List[int] = [1, 8, 16, 32, 64],
        num_samples: int = 100,
        force_cpu: bool = False,
        compute_units: str = "ALL"
    ) -> List[BenchmarkResult]:
        """
        Run benchmarks with different configurations.
        
        Args:
            model_name: Model to benchmark
            batch_sizes: Batch sizes to test
            num_samples: Number of test samples
            force_cpu: Force CPU usage
            compute_units: CoreML compute units to use
            
        Returns:
            List of benchmark results
        """
        results = []
        test_data = self.generate_test_data(num_samples)
        
        for batch_size in batch_sizes:
            try:
                # Create manager for this configuration
                manager = EmbeddingsManagerFactory.create(
                    model_name=model_name,
                    cache_dir=self.cache_dir,
                    force_cpu=force_cpu,
                    compute_units=compute_units
                )
                
                # Warm up
                logger.info(f"Warming up with batch size {batch_size}")
                warmup_data = test_data[:batch_size]
                await manager.get_embeddings(warmup_data, use_cache=False, batch_size=batch_size)
                
                # Measure memory before test
                import psutil
                process = psutil.Process()
                start_mem = process.memory_info().rss / 1024 / 1024  # MB
                
                # Run benchmark
                logger.info(f"Running benchmark with batch size {batch_size}")
                start_time = time.time()
                embeddings, _ = await manager.get_embeddings(
                    test_data,
                    use_cache=False,
                    batch_size=batch_size
                )
                end_time = time.time()
                
                # Calculate metrics
                total_time = end_time - start_time
                avg_latency = (total_time * 1000) / len(test_data)  # ms
                
                # Estimate tokens/sec (rough approximation)
                total_chars = sum(len(chunk.content) for chunk in test_data)
                approx_tokens = total_chars / 4  # rough estimate
                throughput = approx_tokens / total_time
                
                # Measure memory after test
                end_mem = process.memory_info().rss / 1024 / 1024  # MB
                memory_used = end_mem - start_mem
                
                # Create result
                result = BenchmarkResult(
                    model_name=model_name,
                    device=manager.device,
                    batch_size=batch_size,
                    num_samples=num_samples,
                    avg_latency_ms=avg_latency,
                    throughput=throughput,
                    memory_mb=memory_used,
                    compute_units=compute_units
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error benchmarking batch size {batch_size}: {str(e)}")
                continue
        
        return results
    
    def get_optimal_config(
        self,
        max_memory_mb: Optional[float] = None,
        min_throughput: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get optimal configuration based on constraints.
        
        Args:
            max_memory_mb: Maximum memory usage in MB
            min_throughput: Minimum throughput in tokens/second
            
        Returns:
            Dictionary with optimal configuration
        """
        if not self.previous_results:
            return {}
            
        # Filter results based on constraints
        valid_results = self.previous_results
        
        if max_memory_mb is not None:
            valid_results = [
                r for r in valid_results 
                if r.memory_mb <= max_memory_mb
            ]
            
        if min_throughput is not None:
            valid_results = [
                r for r in valid_results
                if r.throughput >= min_throughput
            ]
            
        if not valid_results:
            return {}
            
        # Find result with highest throughput
        optimal = max(valid_results, key=lambda x: x.throughput)
        return optimal.to_dict() 