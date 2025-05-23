from typing import List, Dict, Any, Optional
import os
import json
from pathlib import Path
import logging
import numpy as np
from datetime import datetime
import aiofiles
import asyncio
from tqdm import tqdm

from src.processors.chunking import ChunkingStrategy, MarkdownChunker
from src.embeddings.embeddings_manager import EmbeddingsManager
from src.utils import setup_logging

logger = logging.getLogger(__name__)

class VaultManager:
    def __init__(self):
        self.embeddings_manager = EmbeddingsManager()
        self.chunker = MarkdownChunker()
        self.config_dir = Path(os.getenv("RAG_CONFIG_DIR", "~/.config/obsidian-rag"))
        self.config_dir = self.config_dir.expanduser()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.load_config()
        
    def load_config(self) -> None:
        """Load vault configurations."""
        config_file = self.config_dir / "vaults.json"
        if config_file.exists():
            with open(config_file) as f:
                self.vaults = json.load(f)
        else:
            self.vaults = {}
            
    def save_config(self) -> None:
        """Save vault configurations."""
        config_file = self.config_dir / "vaults.json"
        with open(config_file, "w") as f:
            json.dump(self.vaults, f, indent=2)
            
    async def index_vault(self, vault_name: str) -> Dict[str, Any]:
        """Index or reindex a vault."""
        if vault_name not in self.vaults:
            raise ValueError(f"Vault {vault_name} not found")
            
        vault = self.vaults[vault_name]
        vault_path = Path(vault["path"])
        
        if not vault_path.exists():
            raise ValueError(f"Vault path {vault_path} does not exist")
            
        # Get all markdown files
        markdown_files = list(vault_path.rglob("*.md"))
        total_files = len(markdown_files)
        processed_files = 0
        chunks = []
        
        # Process files with progress bar
        with tqdm(total=total_files, desc="Indexing vault") as pbar:
            for file_path in markdown_files:
                try:
                    async with aiofiles.open(file_path) as f:
                        content = await f.read()
                        
                    # Get chunks
                    file_chunks = self.chunker.chunk(content)
                    
                    # Add metadata
                    for chunk in file_chunks:
                        chunk["source"] = str(file_path.relative_to(vault_path))
                        chunks.append(chunk)
                        
                    processed_files += 1
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    
        # Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embeddings_manager.get_embeddings(texts)
        
        # Save index
        index_dir = self.config_dir / "indices" / vault_name
        index_dir.mkdir(parents=True, exist_ok=True)
        
        np.save(str(index_dir / "embeddings.npy"), embeddings)
        with open(index_dir / "chunks.json", "w") as f:
            json.dump(chunks, f)
            
        # Update vault metadata
        self.vaults[vault_name]["last_indexed"] = datetime.now().isoformat()
        self.vaults[vault_name]["total_chunks"] = len(chunks)
        self.save_config()
        
        return {
            "processed_files": processed_files,
            "total_files": total_files,
            "total_chunks": len(chunks)
        }
        
    async def search(
        self,
        query: str,
        max_results: int = 5,
        vault_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant chunks in the vault."""
        if vault_name and vault_name not in self.vaults:
            raise ValueError(f"Vault {vault_name} not found")
            
        # Get query embedding
        query_embedding = await self.embeddings_manager.get_embeddings([query])
        query_embedding = query_embedding[0]
        
        results = []
        
        # Search in specified vault or all vaults
        vaults_to_search = [vault_name] if vault_name else self.vaults.keys()
        
        for vault in vaults_to_search:
            index_dir = self.config_dir / "indices" / vault
            if not index_dir.exists():
                continue
                
            # Load embeddings and chunks
            embeddings = np.load(str(index_dir / "embeddings.npy"))
            with open(index_dir / "chunks.json") as f:
                chunks = json.load(f)
                
            # Calculate similarities
            similarities = np.dot(embeddings, query_embedding)
            
            # Get top results
            top_indices = np.argsort(similarities)[-max_results:][::-1]
            
            for idx in top_indices:
                chunk = chunks[idx]
                results.append({
                    "content": chunk["text"],
                    "source": chunk["source"],
                    "similarity": float(similarities[idx])
                })
                
        # Sort by similarity and return top results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:max_results]
        
    async def list_vaults(self) -> List[Dict[str, Any]]:
        """List all configured vaults."""
        return [
            {
                "name": name,
                **config
            }
            for name, config in self.vaults.items()
        ] 