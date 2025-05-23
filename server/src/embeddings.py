import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import os
import platform
import logging
import coremltools as ct
from pathlib import Path

logger = logging.getLogger(__name__)

class EmbeddingsManager:
    def __init__(self):
        self.model_name = os.getenv("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
        self.use_neural_engine = self._should_use_neural_engine()
        self.model = self._load_model()
        self.device = self._get_device()
        
    def _should_use_neural_engine(self) -> bool:
        """Check if we should use the Apple Neural Engine."""
        if not os.getenv("RAG_USE_NEURAL_ENGINE", "1") == "1":
            return False
            
        is_mac = platform.system() == "Darwin"
        is_arm = platform.machine() == "arm64"
        return is_mac and is_arm
        
    def _get_device(self) -> torch.device:
        """Get the appropriate device for computations."""
        if self.use_neural_engine:
            return torch.device("mps")
        elif torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")
        
    def _load_model(self) -> SentenceTransformer:
        """Load the embedding model with optimizations."""
        model = SentenceTransformer(self.model_name)
        
        if self.use_neural_engine:
            try:
                self._optimize_for_neural_engine(model)
            except Exception as e:
                logger.warning(f"Failed to optimize for Neural Engine: {e}")
                
        return model
        
    def _optimize_for_neural_engine(self, model: SentenceTransformer) -> None:
        """Optimize the model for Apple Neural Engine."""
        cache_dir = Path(os.getenv("RAG_CACHE_DIR", "~/.cache/obsidian-rag"))
        cache_dir = cache_dir.expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        model_cache = cache_dir / f"{self.model_name}.mlmodel"
        
        if not model_cache.exists():
            # Convert to Core ML format
            traced_model = torch.jit.trace(
                model,
                torch.randn(1, 384, device=self.device)  # Example input
            )
            
            mlmodel = ct.convert(
                traced_model,
                inputs=[ct.TensorType(shape=(1, 384))],
                compute_units=ct.ComputeUnit.ALL  # Use Neural Engine when available
            )
            
            mlmodel.save(str(model_cache))
            
    async def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        try:
            # Convert texts to tensors and move to appropriate device
            embeddings = self.model.encode(
                texts,
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=False
            )
            
            # Convert to numpy and normalize
            embeddings = embeddings.cpu().numpy()
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            normalized_embeddings = embeddings / norms
            
            return normalized_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
            
    async def run_benchmark(self) -> Dict[str, Any]:
        """Run performance benchmarks and return optimal settings."""
        results = {
            "platform": {
                "system": platform.system(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
                "torch_version": torch.__version__
            },
            "compute_units": "NEURAL_ENGINE" if self.use_neural_engine else "CPU",
            "model_name": self.model_name,
            "device": str(self.device)
        }
        
        # Test different batch sizes
        batch_sizes = [1, 4, 8, 16, 32]
        timing_results = {}
        
        for batch_size in batch_sizes:
            texts = ["benchmark text"] * batch_size
            start_time = torch.cuda.Event(enable_timing=True)
            end_time = torch.cuda.Event(enable_timing=True)
            
            start_time.record()
            await self.get_embeddings(texts)
            end_time.record()
            
            torch.cuda.synchronize()
            elapsed_time = start_time.elapsed_time(end_time)
            timing_results[batch_size] = elapsed_time
            
        results["benchmarks"] = {
            "batch_sizes": timing_results,
            "optimal_batch_size": min(timing_results, key=timing_results.get)
        }
        
        return results 