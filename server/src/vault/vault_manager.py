from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, List, Callable, Optional, Any
import os
import json
import logging
from pathlib import Path
import threading
import time
import asyncio
from src.embeddings.embeddings_manager import EmbeddingsManager
from src.processors.file_processor import FileProcessor
from src.processors.chunking import Chunk
import numpy as np
from ..config import Config

logger = logging.getLogger(__name__)

class VaultEventHandler(FileSystemEventHandler):
    """Handles file system events for a vault."""
    
    def __init__(self, on_change: Callable[[str], None]):
        """
        Initialize the event handler.
        
        Args:
            on_change: Callback function to handle file changes
        """
        self.on_change = on_change
        self._debounce_timers: Dict[str, threading.Timer] = {}
        
    def on_modified(self, event):
        if not event.is_directory:
            self._debounce_file_event(event.src_path)
    
    def on_created(self, event):
        if not event.is_directory:
            self._debounce_file_event(event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self._debounce_file_event(event.src_path)
            
    def _debounce_file_event(self, file_path: str, delay: float = 1.0):
        """Debounce file events to prevent multiple rapid updates."""
        if file_path in self._debounce_timers:
            self._debounce_timers[file_path].cancel()
            
        timer = threading.Timer(delay, self.on_change, args=[file_path])
        self._debounce_timers[file_path] = timer
        timer.start()

class VaultManager:
    """Manages Obsidian vaults and file watching."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize vault manager.
        
        Args:
            config_dir: Directory for configuration files
        """
        if config_dir is None:
            config_dir = "~/.config/obsidian-rag"
            
        self.config_dir = Path(config_dir).expanduser()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Set cache directory for embeddings
        os.environ["RAG_CACHE_DIR"] = str(self.config_dir / "embeddings_cache")
        
        # Initialize components
        self.embeddings_manager = EmbeddingsManager()
        self.file_processor = FileProcessor()
        self.vaults: Dict[str, Dict[str, Any]] = {}
        self.observers: Dict[str, Observer] = {}
        
        # Load existing vaults
        self._load_vaults()
    
    def add_vault(
        self,
        name: str,
        path: str,
        file_types: List[str] = None,
        enabled: bool = True
    ) -> dict:
        """
        Add a new vault configuration.
        
        Args:
            name: Unique name for the vault
            path: Path to the vault directory
            file_types: List of file extensions to watch
            enabled: Whether the vault is enabled
            
        Returns:
            Vault configuration dictionary
        """
        if name in self.vaults:
            raise ValueError(f"Vault '{name}' already exists")
            
        if not os.path.isdir(path):
            raise ValueError(f"Invalid vault path: {path}")
            
        vault_config = {
            "name": name,
            "path": path,
            "file_types": file_types or ["md"],
            "enabled": enabled
        }
        
        # Save configuration
        self.save_config(name, vault_config)
        
        # Start watching if enabled
        if enabled:
            self._start_watching(name, vault_config)
            
        self.vaults[name] = vault_config
        return vault_config
    
    def remove_vault(self, name: str):
        """Remove a vault configuration."""
        if name not in self.vaults:
            raise ValueError(f"Vault '{name}' not found")
            
        # Stop watching
        if name in self.observers:
            self.observers[name].stop()
            self.observers[name].join()
            del self.observers[name]
            
        # Remove configuration
        config_path = self.config_dir / f"{name}.json"
        if config_path.exists():
            config_path.unlink()
            
        del self.vaults[name]
    
    def get_vault(self, name: str) -> Optional[dict]:
        """Get vault configuration by name."""
        return self.vaults.get(name)
    
    def list_vaults(self) -> List[dict]:
        """List all vault configurations."""
        return list(self.vaults.values())
    
    def enable_vault(self, name: str):
        """Enable a vault."""
        if name not in self.vaults:
            raise ValueError(f"Vault '{name}' not found")
            
        vault_config = self.vaults[name]
        vault_config["enabled"] = True
        
        self.save_config(name, vault_config)
        self._start_watching(name, vault_config)
    
    def disable_vault(self, name: str):
        """Disable a vault."""
        if name not in self.vaults:
            raise ValueError(f"Vault '{name}' not found")
            
        vault_config = self.vaults[name]
        vault_config["enabled"] = False
        
        self.save_config(name, vault_config)
        
        if name in self.observers:
            self.observers[name].stop()
            self.observers[name].join()
            del self.observers[name]
    
    def save_config(self, name: str, config: dict):
        """Save vault configuration to disk."""
        config_path = self.config_dir / f"{name}.json"
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving vault config {name}: {str(e)}")
    
    async def index_vault(self, name: str) -> dict:
        """Index a vault's contents."""
        if name not in self.vaults:
            raise ValueError(f"Vault '{name}' not found")
            
        vault_config = self.vaults[name]
        vault_path = Path(vault_config["path"])
        
        if not vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")
            
        # Process files
        chunks = []
        processed_files = 0
        total_files = 0
        
        for file_type in vault_config["file_types"]:
            for file_path in vault_path.rglob(f"*.{file_type}"):
                total_files += 1
                try:
                    file_chunks = self.file_processor.process_file(str(file_path))
                    chunks.extend(file_chunks)
                    processed_files += 1
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
        
        # Generate embeddings
        embeddings, _ = await self.embeddings_manager.get_embeddings(chunks)
        
        # Save index with content included
        index_dir = self.config_dir / "indices" / name
        index_dir.mkdir(parents=True, exist_ok=True)
        
        np.save(str(index_dir / "embeddings.npy"), embeddings)
        with open(index_dir / "chunks.json", "w") as f:
            json.dump([{"content": c.content, **c.metadata} for c in chunks], f)
        
        return {
            "processed_files": processed_files,
            "total_files": total_files,
            "total_chunks": len(chunks)
        }
    
    async def search(
        self,
        query: str,
        vault_name: Optional[str] = None,
        max_results: int = 5
    ) -> List[dict]:
        """Search for content in vault(s)."""
        results = []
        
        # Determine which vaults to search
        search_vaults = [vault_name] if vault_name else self.vaults.keys()
        
        for name in search_vaults:
            if name not in self.vaults:
                if vault_name:  # Only raise error if specific vault was requested
                    raise ValueError(f"Vault '{name}' not found")
                continue
                
            index_dir = self.config_dir / "indices" / name
            if not index_dir.exists():
                continue
                
            try:
                # Load index
                embeddings = np.load(str(index_dir / "embeddings.npy"))
                with open(index_dir / "chunks.json") as f:
                    chunks = json.load(f)
                
                # Extract texts for search
                texts = [chunk["content"] for chunk in chunks]
                
                # Search
                vault_results = await self.embeddings_manager.search(
                    query,
                    embeddings,
                    texts,
                    max_results=max_results
                )
                
                # Add vault name and metadata to results
                for i, result in enumerate(vault_results):
                    result["vault"] = name
                    result["content"] = result.pop("text")  # Rename text to content
                    # Add any additional metadata from the chunk
                    result.update({
                        k: v for k, v in chunks[i].items()
                        if k not in ["content", "similarity"]
                    })
                
                results.extend(vault_results)
                
            except Exception as e:
                logger.error(f"Error searching vault {name}: {str(e)}")
        
        # Sort by similarity and limit results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:max_results]
    
    def _load_vaults(self):
        """Load vault configurations from disk."""
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, "r") as f:
                    vault_config = json.load(f)
                    
                name = vault_config["name"]
                self.vaults[name] = vault_config
                
                if vault_config["enabled"]:
                    self._start_watching(name, vault_config)
                    
            except Exception as e:
                logger.error(f"Error loading vault config {config_file}: {str(e)}")
    
    def _start_watching(self, name: str, config: dict):
        """Start watching a vault directory."""
        if name in self.observers:
            self.observers[name].stop()
            self.observers[name].join()
            
        try:
            observer = Observer()
            handler = VaultEventHandler(
                on_change=lambda path: logger.info(f"File changed: {path}")
            )
            
            observer.schedule(handler, config["path"], recursive=True)
            observer.start()
            
            self.observers[name] = observer
            
        except Exception as e:
            logger.error(f"Error starting vault watcher for {name}: {str(e)}")
            
    def __del__(self):
        """Clean up observers on deletion."""
        for observer in self.observers.values():
            observer.stop()
            observer.join() 