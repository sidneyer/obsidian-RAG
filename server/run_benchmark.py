"""Script to run embeddings benchmarks."""
import asyncio
import json
from pathlib import Path
from src.embeddings.benchmark import EmbeddingsBenchmark
from src.embeddings.factory import EmbeddingsManagerFactory

async def main():
    """Run benchmarks with different configurations."""
    # Initialize benchmark
    results_file = Path("benchmark_results.json")
    benchmark = EmbeddingsBenchmark(results_file=str(results_file))
    
    # Test configurations
    model_names = ["all-MiniLM-L6-v2"]  # Add more models if needed
    batch_sizes = [1, 8, 16, 32]
    num_samples = 100
    
    print("\nRunning benchmarks...")
    print("=" * 50)
    
    all_results = []
    for model_name in model_names:
        print(f"\nTesting model: {model_name}")
        try:
            results = await benchmark.run_benchmark(
                model_name=model_name,
                batch_sizes=batch_sizes,
                num_samples=num_samples
            )
            all_results.extend(results)
            
            # Print results for this model
            for result in results:
                print(f"\nBatch size: {result.batch_size}")
                print(f"Average latency: {result.avg_latency_ms:.2f}ms")
                print(f"Throughput: {result.throughput:.2f} tokens/sec")
                print(f"Memory usage: {result.memory_mb:.2f}MB")
                print(f"Device: {result.device}")
                print("-" * 30)
                
        except Exception as e:
            print(f"Error testing {model_name}: {str(e)}")
    
    print("\nBenchmark complete!")
    print(f"Results saved to: {results_file}")
    
    # Get optimal configuration
    optimal = benchmark.get_optimal_config()
    if optimal:
        print("\nOptimal configuration:")
        print(f"Model: {optimal['model_name']}")
        print(f"Batch size: {optimal['batch_size']}")
        print(f"Throughput: {optimal['throughput']:.2f} tokens/sec")
        print(f"Memory usage: {optimal['memory_mb']:.2f}MB")

if __name__ == "__main__":
    asyncio.run(main()) 