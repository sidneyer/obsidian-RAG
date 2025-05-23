from typing import List, Dict, Any, Optional
import logging
import os
from pathlib import Path
import json
from datetime import datetime

from ..processors.file_processor import FileProcessor
from ..embeddings.embeddings_manager import EmbeddingsManager
from ..llm.llm_manager import LLMManager
from ..vault.vault_manager import VaultManager

logger = logging.getLogger(__name__)

class RAGService:
    """RAG service for Obsidian."""
    
    def __init__(self, base_dir: str, llm_model_path: str):
        """Initialize RAG service.
        
        Args:
            base_dir: Base directory for configuration and cache
            llm_model_path: Path to LLM model file
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize managers
        self.embeddings_manager = EmbeddingsManager(
            cache_dir=str(self.base_dir / "embeddings_cache")
        )
        self.llm_manager = LLMManager(
            model_path=llm_model_path
        )
        self.vault_manager = VaultManager(
            config_dir=str(self.base_dir / "vault_config")
        )
        
        # Initialize chunk storage
        self.chunks = {}
    
    async def register_vault(
        self,
        name: str,
        path: str,
        file_types: List[str],
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Register a vault.
        
        Args:
            name: Vault name
            path: Vault path
            file_types: List of file types to process
            enabled: Whether the vault is enabled
            
        Returns:
            Dict: Vault configuration
        """
        return self.vault_manager.add_vault(
            name=name,
            path=path,
            file_types=file_types,
            enabled=enabled
        )
    
    async def process_vault(self, vault_name: str) -> Dict[str, Any]:
        """Process a vault.
        
        Args:
            vault_name: Name of the vault to process
            
        Returns:
            Dict: Processing statistics
        """
        return await self.vault_manager.index_vault(vault_name)
    
    async def query(
        self,
        query: str,
        vault_name: Optional[str] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Query the RAG system.
        
        Args:
            query: User's question
            vault_name: Optional vault to restrict search to
            max_results: Maximum number of results
            
        Returns:
            Dict: Response and sources
            
        Raises:
            ValueError: If no vaults are configured
        """
        vaults = await self.list_vaults()
        if not vaults:
            raise ValueError("No vaults configured")
        
        # Get relevant chunks
        results = await self.vault_manager.search(
            query,
            vault_name=vault_name,
            max_results=max_results
        )
        
        if not results:
            return {
                "response": "No relevant information found.",
                "sources": []
            }
        
        # Create prompt
        context = "\n\n".join([
            f"{r['content']}\n[Source: {r['source']}]"
            for r in results
        ])
        
        system_prompt = """You are a helpful AI assistant answering questions based on the provided context.
Use the following context to answer the question. If you cannot answer the question based on the context,
say so clearly. Do not make up information."""
        
        user_prompt = f"""Context:
{context}

Question: {query}

Answer:"""
        
        # Generate response
        response = await self.llm_manager.generate(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        return {
            "response": response,
            "sources": [
                {
                    "content": r["content"],
                    "source": r["source"],
                    "similarity": r["similarity"]
                }
                for r in results
            ]
        }
    
    async def list_vaults(self) -> List[Dict[str, Any]]:
        """List registered vaults.
        
        Returns:
            List[Dict]: List of vault configurations
        """
        return self.vault_manager.list_vaults()
    
    async def enable_vault(self, vault_name: str):
        """Enable a vault.
        
        Args:
            vault_name: Name of the vault to enable
        """
        self.vault_manager.enable_vault(vault_name)
    
    async def disable_vault(self, vault_name: str):
        """Disable a vault.
        
        Args:
            vault_name: Name of the vault to disable
        """
        self.vault_manager.disable_vault(vault_name)
    
    async def remove_vault(self, vault_name: str):
        """Remove a vault.
        
        Args:
            vault_name: Name of the vault to remove
        """
        self.vault_manager.remove_vault(vault_name)
    
    def _setup_vault_handler(self):
        """Set up handler for vault file changes."""
        def handle_file_change(file_path: str):
            try:
                # Remove old chunks if file was deleted
                if not os.path.exists(file_path):
                    if file_path in self.chunks:
                        del self.chunks[file_path]
                        self._save_chunks()
                    return
                    
                # Process changed/new file
                chunks = self.file_processor.process_file(file_path)
                if chunks:
                    self.chunks[file_path] = chunks
                    self._save_chunks()
                    
            except Exception as e:
                logger.error(f"Error handling file change {file_path}: {str(e)}")
        
        # Update vault manager's handler
        for name, config in self.vault_manager.vaults.items():
            if config["enabled"]:
                self.vault_manager._start_watching(
                    name,
                    config,
                    on_change=handle_file_change
                )
    
    def _load_chunks(self):
        """Load chunks from disk."""
        chunks_file = self.chunks_dir / "chunks.json"
        if chunks_file.exists():
            try:
                with open(chunks_file, "r") as f:
                    self.chunks = json.load(f)
            except Exception as e:
                logger.error(f"Error loading chunks: {str(e)}")
                self.chunks = {}
    
    def _save_chunks(self):
        """Save chunks to disk."""
        chunks_file = self.chunks_dir / "chunks.json"
        try:
            with open(chunks_file, "w") as f:
                json.dump(self.chunks, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving chunks: {str(e)}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        return {
            "total_files": len(self.chunks),
            "total_chunks": sum(len(chunks) for chunks in self.chunks.values()),
            "vaults": len(self.vault_manager.vaults),
            "last_updated": datetime.now().isoformat()
        } 