import json
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.rag.rag_service import RAGService

# Load configuration
config_path = Path(__file__).parent / "config" / "config.json"
with open(config_path) as f:
    config = json.load(f)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config["logging"]["level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=config["logging"]["file"] if "file" in config["logging"] else None
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Obsidian RAG Server",
    description="Local RAG server for Obsidian vaults",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config["security"]["allowed_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG service
base_dir = Path(config["rag"]["base_dir"])
base_dir.mkdir(parents=True, exist_ok=True)

rag_service = RAGService(
    base_dir=str(base_dir),
    llm_model_path=config["rag"]["llm"]["model_path"],
    embedding_model_name=config["rag"]["embeddings"]["model_name"]
)

# Models
class VaultConfig(BaseModel):
    name: str
    path: str
    file_types: List[str] = ["md"]
    enabled: bool = True

class ChatRequest(BaseModel):
    query: str
    vault_name: Optional[str] = None

# Security
async def verify_api_key(x_api_key: str = Header(None)):
    if config["security"]["api_key_required"]:
        api_key = os.getenv("OBSIDIAN_RAG_API_KEY")
        if not api_key or x_api_key != api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )

# Routes
@app.get("/")
async def root():
    """Get server status."""
    return {
        "status": "running",
        "version": "0.1.0",
        "stats": rag_service.get_stats()
    }

@app.post("/vault")
async def add_vault(
    config: VaultConfig,
    _: None = Depends(verify_api_key)
):
    """Register a new vault."""
    try:
        vault = rag_service.vault_manager.add_vault(
            name=config.name,
            path=config.path,
            file_types=config.file_types,
            enabled=config.enabled
        )
        return {"status": "success", "vault": vault}
    except Exception as e:
        logger.error(f"Error adding vault: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vault/{name}/process")
async def process_vault(
    name: str,
    _: None = Depends(verify_api_key)
):
    """Process all files in a vault."""
    try:
        stats = rag_service.process_vault(name)
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Error processing vault: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(
    request: ChatRequest,
    _: None = Depends(verify_api_key)
):
    """Query the RAG system."""
    try:
        response = rag_service.query(
            query=request.query,
            vault_name=request.vault_name
        )
        return response
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vaults")
async def list_vaults(_: None = Depends(verify_api_key)):
    """List all registered vaults."""
    return rag_service.vault_manager.list_vaults()

if __name__ == "__main__":
    logger.info("Starting Obsidian RAG server...")
    uvicorn.run(
        "run:app",
        host=config["server"]["host"],
        port=config["server"]["port"],
        reload=config["server"]["debug"]
    ) 