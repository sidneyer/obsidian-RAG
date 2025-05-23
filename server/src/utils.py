import logging
import os
import platform
import psutil
import torch
from typing import Dict, Any

def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    log_level = os.getenv("RAG_LOG_LEVEL", "INFO")
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format
    )
    
    # Create logger for this module
    logger = logging.getLogger("obsidian-rag")
    
    # Add file handler if log file is specified
    log_file = os.getenv("RAG_LOG_FILE")
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
        
    return logger

def get_platform_info() -> Dict[str, Any]:
    """Get detailed platform and system information."""
    cpu_info = {
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
        "usage": psutil.cpu_percent(interval=1, percpu=True)
    }
    
    memory = psutil.virtual_memory()
    memory_info = {
        "total": memory.total,
        "available": memory.available,
        "percent": memory.percent
    }
    
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "name": torch.cuda.get_device_name(0),
            "count": torch.cuda.device_count(),
            "memory": {
                "allocated": torch.cuda.memory_allocated(0),
                "cached": torch.cuda.memory_reserved(0)
            }
        }
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        gpu_info = {
            "name": "Apple M-series GPU",
            "type": "MPS",
            "available": True
        }
        
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "cpu": cpu_info,
        "memory": memory_info,
        "gpu": gpu_info
    }

def get_cache_dir() -> str:
    """Get the cache directory path."""
    cache_dir = os.getenv("RAG_CACHE_DIR")
    if cache_dir:
        return cache_dir
        
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Caches/obsidian-rag")
    elif platform.system() == "Linux":
        return os.path.expanduser("~/.cache/obsidian-rag")
    else:  # Windows
        return os.path.join(os.getenv("LOCALAPPDATA", ""), "obsidian-rag", "cache")

def get_config_dir() -> str:
    """Get the configuration directory path."""
    config_dir = os.getenv("RAG_CONFIG_DIR")
    if config_dir:
        return config_dir
        
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Application Support/obsidian-rag")
    elif platform.system() == "Linux":
        return os.path.expanduser("~/.config/obsidian-rag")
    else:  # Windows
        return os.path.join(os.getenv("APPDATA", ""), "obsidian-rag") 