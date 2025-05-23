"""Factory for creating the appropriate embeddings manager based on platform."""
import platform
import logging
from typing import Optional
from .embeddings_manager import EmbeddingsManager
from .apple_embeddings import AppleEmbeddingsManager

logger = logging.getLogger(__name__)

class EmbeddingsManagerFactory:
    """Factory for creating embeddings managers."""
    
    @staticmethod
    def create(
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[str] = None,
        force_cpu: bool = False,
        compute_units: str = "ALL"
    ) -> EmbeddingsManager:
        """
        Create an appropriate embeddings manager based on platform.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            cache_dir: Directory to cache embeddings and models
            force_cpu: Force CPU usage even if better options available
            compute_units: CoreML compute units (for Apple Silicon)
            
        Returns:
            An instance of EmbeddingsManager or its subclasses
        """
        if force_cpu:
            logger.info("Forcing CPU usage as requested")
            return EmbeddingsManager(
                model_name=model_name,
                cache_dir=cache_dir,
                device="cpu"
            )
        
        # Check for Apple Silicon
        if (platform.system() == "Darwin" and 
            platform.processor() == "arm"):
            logger.info("Apple Silicon detected, using optimized implementation")
            return AppleEmbeddingsManager(
                model_name=model_name,
                cache_dir=cache_dir,
                compute_units=compute_units
            )
        
        # Check for CUDA
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("CUDA GPU detected")
                return EmbeddingsManager(
                    model_name=model_name,
                    cache_dir=cache_dir,
                    device="cuda"
                )
        except ImportError:
            pass
        
        logger.info("Using CPU implementation")
        return EmbeddingsManager(
            model_name=model_name,
            cache_dir=cache_dir,
            device="cpu"
        ) 