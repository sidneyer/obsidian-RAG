"""Configuration management for the RAG system."""
from typing import Optional, Dict, Any
from pathlib import Path
import json
import logging
from pydantic import BaseModel, Field
import platform

logger = logging.getLogger(__name__)

class EmbeddingsConfig(BaseModel):
    """Configuration for embeddings system."""
    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="Name of the sentence-transformers model to use"
    )
    cache_dir: Optional[str] = Field(
        default=None,
        description="Directory for caching embeddings and models"
    )
    force_cpu: bool = Field(
        default=False,
        description="Force CPU usage even if better options available"
    )
    compute_units: str = Field(
        default="ALL",
        description="CoreML compute units (ALL, CPU_AND_NE, CPU_ONLY)"
    )
    batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation"
    )
    max_length: int = Field(
        default=384,
        description="Maximum sequence length for tokenization"
    )

class ChunkingConfig(BaseModel):
    """Configuration for text chunking."""
    chunk_size: int = Field(
        default=500,
        description="Target size for text chunks"
    )
    chunk_overlap: int = Field(
        default=50,
        description="Overlap between consecutive chunks"
    )
    preserve_markdown: bool = Field(
        default=True,
        description="Preserve Markdown structure when chunking"
    )

class CacheConfig(BaseModel):
    """Configuration for caching system."""
    embeddings_cache: bool = Field(
        default=True,
        description="Enable embeddings cache"
    )
    models_cache: bool = Field(
        default=True,
        description="Enable models cache"
    )
    max_cache_size_mb: int = Field(
        default=1024,
        description="Maximum cache size in MB"
    )
    cache_cleanup_interval: int = Field(
        default=3600,
        description="Cache cleanup interval in seconds"
    )

class SystemConfig(BaseModel):
    """System-wide configuration."""
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    max_concurrent_requests: int = Field(
        default=10,
        description="Maximum number of concurrent requests"
    )
    timeout_seconds: int = Field(
        default=30,
        description="Request timeout in seconds"
    )

class Config(BaseModel):
    """Main configuration class."""
    embeddings: EmbeddingsConfig = Field(
        default_factory=EmbeddingsConfig,
        description="Embeddings configuration"
    )
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Chunking configuration"
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Cache configuration"
    )
    system: SystemConfig = Field(
        default_factory=SystemConfig,
        description="System configuration"
    )
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """
        Load configuration from file or create default.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Config instance
        """
        if config_path and Path(config_path).exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                return cls(**data)
            except Exception as e:
                logger.error(f"Error loading config from {config_path}: {str(e)}")
                logger.warning("Using default configuration")
        
        # Create platform-specific defaults
        config = cls()
        
        # Optimize for Apple Silicon
        if platform.system() == "Darwin" and platform.processor() == "arm":
            config.embeddings.compute_units = "ALL"
            config.embeddings.batch_size = 16  # Good default for Neural Engine
            
            # Increase cache sizes for desktop use
            config.cache.max_cache_size_mb = 2048
        
        # Optimize for other platforms
        elif platform.system() == "Linux":
            # Typical server configuration
            config.embeddings.batch_size = 64
            config.system.max_concurrent_requests = 20
        
        return config
    
    def save(self, config_path: str) -> None:
        """
        Save configuration to file.
        
        Args:
            config_path: Path to save configuration
        """
        try:
            with open(config_path, 'w') as f:
                json.dump(self.dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {str(e)}")
    
    def update_from_benchmark(self, benchmark_results: Dict[str, Any]) -> None:
        """
        Update configuration based on benchmark results.
        
        Args:
            benchmark_results: Results from benchmarking
        """
        self.embeddings.model_name = benchmark_results["model_name"]
        self.embeddings.batch_size = benchmark_results["batch_size"]
        
        if benchmark_results.get("compute_units"):
            self.embeddings.compute_units = benchmark_results["compute_units"]
        
        # Adjust cache size based on model memory usage
        memory_mb = benchmark_results.get("expected_memory_mb", 0)
        if memory_mb:
            # Set cache size to at least 2x model size
            self.cache.max_cache_size_mb = max(
                self.cache.max_cache_size_mb,
                int(memory_mb * 2)
            )
    
    def validate_resources(self) -> bool:
        """
        Validate system resources against configuration.
        
        Returns:
            bool: True if configuration is valid for system
        """
        import psutil
        
        # Check available memory
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        required_mb = (
            self.cache.max_cache_size_mb +
            self.embeddings.batch_size * 50  # Rough estimate per batch
        )
        
        if available_mb < required_mb:
            logger.warning(
                f"Insufficient memory: {available_mb:.0f}MB available, "
                f"{required_mb:.0f}MB required"
            )
            return False
        
        # Check CPU cores for concurrent requests
        cpu_count = psutil.cpu_count()
        if cpu_count and self.system.max_concurrent_requests > cpu_count * 2:
            logger.warning(
                f"High concurrent requests ({self.system.max_concurrent_requests}) "
                f"for available CPUs ({cpu_count})"
            )
            return False
        
        return True 