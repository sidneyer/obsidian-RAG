"""LLM Manager for handling local language model inference with Apple Silicon optimizations."""
from typing import Dict, Any, Optional
import logging
import os
from pathlib import Path
import json
import platform
from datetime import datetime, timedelta
import ctypes
from llama_cpp import Llama
import numpy as np
import torch

logger = logging.getLogger(__name__)

class LLMManager:
    """Manages local LLM inference using llama.cpp with Apple Silicon optimizations."""
    
    def __init__(
        self,
        model_path: str,
        context_size: int = 2048,
        max_tokens: int = 512,
        temperature: float = 0.7,
        cache_dir: Optional[str] = None,
        use_neural_engine: bool = True
    ):
        """Initialize LLM Manager.
        
        Args:
            model_path: Path to the GGUF model file
            context_size: Maximum context size
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            cache_dir: Directory for caching responses
            use_neural_engine: Whether to use Apple Neural Engine (if available)
        """
        self.model_path = Path(model_path).resolve()
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
            
        self.context_size = context_size
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.use_neural_engine = use_neural_engine
        
        # Initialize cache
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
        # Load model with optimizations
        self.model = self._load_model()
        logger.info(f"Loaded model from {self.model_path}")
        
        # Log hardware utilization
        self._log_hardware_info()
        
    def _load_model(self) -> Llama:
        """Load the LLM model with optimizations."""
        try:
            if self._should_use_metal():
                # Configure Metal for Apple Silicon
                n_gpu_layers = -1  # Use all layers on GPU
                logger.info("Using Metal for GPU acceleration")
                
                return Llama(
                    model_path=str(self.model_path),
                    n_ctx=self.context_size,
                    n_gpu_layers=n_gpu_layers,
                    use_mlock=True,
                    use_mmap=True,
                    main_gpu=0,
                    tensor_split=None,  # Auto split between CPU and GPU
                    seed=-1,  # Random seed
                    n_threads=max(1, os.cpu_count() // 2),  # Use half of available cores
                    n_batch=512  # Increased batch size for better performance
                )
            
            # Fallback to CPU
            logger.info("Using CPU for inference")
            return Llama(
                model_path=str(self.model_path),
                n_ctx=self.context_size,
                use_mlock=True,
                use_mmap=True,
                n_threads=max(1, os.cpu_count() // 2)
            )
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
            
    def _should_use_metal(self) -> bool:
        """Check if Metal should be used for GPU acceleration."""
        try:
            is_apple_silicon = (
                platform.system() == "Darwin" and
                platform.machine() == "arm64"
            )
            
            if not is_apple_silicon:
                return False
                
            # Check if Metal is enabled
            metal_enabled = bool(os.getenv("LLAMA_METAL", "1"))
            if not metal_enabled:
                logger.warning("Metal is disabled via LLAMA_METAL environment variable")
                return False
                
            # Check Neural Engine preference
            if self.use_neural_engine:
                try:
                    import coremltools
                    logger.info("Apple Neural Engine is available")
                except ImportError:
                    logger.warning("coremltools not found, falling back to Metal")
                    
            return True
            
        except Exception as e:
            logger.warning(f"Error checking Metal availability: {e}")
            return False
            
    def _log_hardware_info(self):
        """Log information about hardware utilization."""
        import psutil
        
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "frequency": psutil.cpu_freq().max if psutil.cpu_freq() else "Unknown"
        }
        
        memory_info = {
            "total": psutil.virtual_memory().total / (1024 ** 3),  # GB
            "available": psutil.virtual_memory().available / (1024 ** 3)  # GB
        }
        
        gpu_info = {
            "metal_available": self._should_use_metal(),
            "neural_engine_enabled": self.use_neural_engine
        }
        
        logger.info(f"Hardware configuration:")
        logger.info(f"CPU: {cpu_info}")
        logger.info(f"Memory: {memory_info}")
        logger.info(f"GPU: {gpu_info}")
        
    def _get_cache_key(self, prompt: str, system_prompt: str) -> str:
        """Generate a cache key for the given prompts."""
        import hashlib
        combined = f"{prompt}|||{system_prompt}"
        return hashlib.sha256(combined.encode()).hexdigest()
        
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get a cached response if available and not expired."""
        if not self.cache_dir:
            return None
            
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file) as f:
                data = json.load(f)
                
            # Check if cache is expired (24 hours)
            cached_time = datetime.fromisoformat(data["timestamp"])
            if datetime.now() - cached_time > timedelta(hours=24):
                return None
                
            return data["response"]
            
        except Exception as e:
            logger.warning(f"Failed to read cache: {e}")
            return None
            
    def _cache_response(self, cache_key: str, response: str):
        """Cache a response."""
        if not self.cache_dir:
            return
            
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            data = {
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(cache_file, "w") as f:
                json.dump(data, f)
                
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
            
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """Generate a response for the given prompt.
        
        Args:
            prompt: The user's prompt
            system_prompt: Optional system prompt for context
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stream: Whether to stream the response
            
        Returns:
            str: Generated response
        """
        # Check cache first
        cache_key = self._get_cache_key(prompt, system_prompt)
        cached = self._get_cached_response(cache_key)
        if cached:
            logger.debug("Using cached response")
            return cached
            
        try:
            # Prepare the complete prompt
            if system_prompt:
                complete_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                complete_prompt = prompt
                
            # Generate response
            response = self.model(
                complete_prompt,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                echo=False,
                stream=stream
            )
            
            if stream:
                # Handle streaming response
                chunks = []
                for chunk in response:
                    text = chunk["choices"][0]["text"]
                    chunks.append(text)
                    yield text
                generated_text = "".join(chunks)
            else:
                # Handle regular response
                generated_text = response["choices"][0]["text"].strip()
            
            # Cache the response
            self._cache_response(cache_key, generated_text)
            
            if not stream:
                return generated_text
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
            
    def get_stats(self) -> Dict[str, Any]:
        """Get model and hardware statistics."""
        import psutil
        
        stats = {
            "model": {
                "path": str(self.model_path),
                "context_size": self.context_size,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            },
            "hardware": {
                "metal_available": self._should_use_metal(),
                "neural_engine_enabled": self.use_neural_engine,
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent
            },
            "cache": {
                "enabled": bool(self.cache_dir),
                "path": str(self.cache_dir) if self.cache_dir else None
            }
        }
        
        return stats 