from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from dotenv import load_dotenv

from src.embeddings.embeddings_manager import EmbeddingsManager
from src.vault.vault_manager import VaultManager
from src.processors.chunking import ChunkingStrategy
from src.utils import setup_logging, get_platform_info

# Load environment variables
load_dotenv()

# Initialize logging
logger = setup_logging()

app = FastAPI(
    title="Obsidian RAG API",
    description="Local RAG system for Obsidian with Apple Silicon optimization",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
embeddings_manager = EmbeddingsManager()
vault_manager = VaultManager(config_dir=os.getenv("RAG_CONFIG_DIR", "~/.config/obsidian-rag"))

class SearchQuery(BaseModel):
    query: str
    max_results: int = 5
    vault_name: Optional[str] = None

class SearchResult(BaseModel):
    content: str
    source: str
    similarity: float

@app.get("/")
async def root():
    """Get server status and information."""
    platform_info = get_platform_info()
    return {
        "status": "running",
        "version": "0.1.0",
        "platform": platform_info
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/search")
async def search(query: SearchQuery, vault_manager: VaultManager = Depends()):
    """Search through the vault using RAG."""
    try:
        results = await vault_manager.search(
            query.query,
            max_results=query.max_results,
            vault_name=query.vault_name
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index")
async def index_documents(vault_name: str, vault_manager: VaultManager = Depends()):
    """Index or reindex documents in a vault."""
    try:
        stats = await vault_manager.index_vault(vault_name)
        return {"status": "success", "stats": stats}
    except ValueError as e:
        logger.error(f"Indexing error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vaults")
async def list_vaults(vault_manager: VaultManager = Depends()):
    """List all configured vaults."""
    try:
        vaults = await vault_manager.list_vaults()
        return vaults
    except Exception as e:
        logger.error(f"Error listing vaults: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/benchmark")
async def run_benchmark():
    """Run performance benchmarks and optimize settings."""
    try:
        results = await embeddings_manager.run_benchmark()
        return results
    except Exception as e:
        logger.error(f"Benchmark error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("RAG_SERVER_PORT", "8000"))
    host = os.getenv("RAG_SERVER_HOST", "127.0.0.1")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True if os.getenv("RAG_DEBUG") else False
    ) 