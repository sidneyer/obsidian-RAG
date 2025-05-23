"""Manages embeddings for text chunks using sentence-transformers."""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
import os
import json
from pathlib import Path
import hashlib
import platform
import torch
import asyncio
import time
from ..processors.chunking import Chunk
import coremltools as ct

logger = logging.getLogger(__name__)

class EmbeddingsManager:
    """Manages embeddings generation and caching."""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        cache_dir: Optional[str] = None,
        device: Optional[str] = None
    ):
        """Initialize the embeddings manager.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            cache_dir: Directory to cache embeddings and models
            device: Device to use for computations (cpu, cuda, mps)
        """
        self.model_name = model_name or os.getenv("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
        self.cache_dir = cache_dir
        self.use_neural_engine = self._should_use_neural_engine()
        self.device = device if device else self._get_device()
        self.model = SentenceTransformer(self.model_name, device=self.device)
        
        if self.use_neural_engine:
            try:
                self._optimize_for_neural_engine()
            except Exception as e:
                logger.warning(f"Failed to optimize for Neural Engine: {e}")
    
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
    
    def _optimize_for_neural_engine(self) -> None:
        """Optimize the model for Apple Neural Engine."""
        if not self.cache_dir:
            cache_dir = Path(os.getenv("RAG_CACHE_DIR", "~/.cache/obsidian-rag"))
        else:
            cache_dir = Path(self.cache_dir)
            
        cache_dir = cache_dir.expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        model_cache = cache_dir / f"{self.model_name}.mlmodel"
        
        if not model_cache.exists():
            # Convert to Core ML format
            traced_model = torch.jit.trace(
                self.model,
                torch.randn(1, 384, device=self.device)  # Example input
            )
            
            mlmodel = ct.convert(
                traced_model,
                inputs=[ct.TensorType(shape=(1, 384))],
                compute_units=ct.ComputeUnit.ALL  # Use Neural Engine when available
            )
            
            mlmodel.save(str(model_cache))
    
    async def get_embeddings(
        self,
        texts: List[Union[str, Chunk]],
        use_cache: bool = True,
        batch_size: Optional[int] = None
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts or chunks to embed
            use_cache: Whether to use cached embeddings
            batch_size: Batch size for processing
            
        Returns:
            Tuple of (embeddings array, metadata list)
        """
        if not texts:
            raise ValueError("Empty input")
            
        # Convert chunks to texts if needed
        if isinstance(texts[0], Chunk):
            text_contents = [chunk.content for chunk in texts]
            metadata = [chunk.metadata for chunk in texts]
        else:
            text_contents = texts
            metadata = [{"source": f"text_{i}"} for i in range(len(texts))]
            
        try:
            # Convert texts to tensors and move to appropriate device
            embeddings = self.model.encode(
                text_contents,
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=False,
                batch_size=batch_size or 32
            )
            
            # Convert to numpy and normalize
            embeddings = embeddings.cpu().numpy()
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            normalized_embeddings = embeddings / norms
            
            return normalized_embeddings, metadata
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def clear_cache(self):
        """Clear the embeddings cache."""
        cache_dir = Path(os.getenv("RAG_CACHE_DIR", "~/.cache/obsidian-rag")).expanduser()
        if cache_dir.exists():
            for cache_file in cache_dir.glob("*.npy"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete cache file {cache_file}: {e}")
    
    async def search(
        self,
        query: str,
        embeddings: np.ndarray,
        texts: List[str],
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar texts.
        
        Args:
            query: Search query
            embeddings: Pre-computed embeddings
            texts: Original texts corresponding to embeddings
            max_results: Maximum number of results
            
        Returns:
            List[Dict]: Search results with similarity scores
        """
        if len(embeddings) == 0:
            return []
        
        # Get query embedding
        query_embedding = await self.get_embeddings([query])
        query_embedding = query_embedding[0]  # Get first (and only) embedding
        
        # Calculate similarities
        similarities = np.dot(embeddings, query_embedding)
        
        # Get top results
        top_indices = np.argsort(similarities)[-max_results:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                "text": texts[idx],
                "similarity": float(similarities[idx])
            })
        
        return results
    
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
            "device": str(self.device),
            "benchmarks": {}
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
    
    async def get_similar_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Get chunks most similar to query.
        
        Args:
            query: Search query
            chunks: List of chunks
            top_k: Number of chunks to return
            
        Returns:
            List[Dict]: Similar chunks with scores
        """
        # Convert chunks to Chunk objects
        chunk_objects = [
            Chunk(
                content=c["content"],
                metadata=c["metadata"],
                start_char=c.get("start_char", 0),
                end_char=c.get("end_char", len(c["content"]))
            )
            for c in chunks
        ]
        
        # Get embeddings
        embeddings, metadata = await self.get_embeddings(chunk_objects)
        
        # Search
        return await self.search(query, embeddings, metadata, max_results=top_k) 