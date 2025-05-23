"""Base class for file processors."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProcessedChunk:
    """Represents a processed chunk of text with metadata."""
    content: str
    metadata: Dict[str, Any]
    start_pos: int
    end_pos: int

class BaseProcessor(ABC):
    """Base class for file processors."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        preserve_markdown: bool = True
    ):
        """Initialize the processor.
        
        Args:
            chunk_size: Target size for text chunks
            chunk_overlap: Number of characters to overlap between chunks
            preserve_markdown: Whether to preserve markdown formatting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_markdown = preserve_markdown
        
    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if this processor can handle the file
        """
        pass
        
    @abstractmethod
    async def process(self, file_path: str) -> List[ProcessedChunk]:
        """Process a file into chunks.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            List[ProcessedChunk]: List of processed chunks
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file can't be processed
        """
        pass
        
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace.
        
        Args:
            text: Text to clean
            
        Returns:
            str: Cleaned text
        """
        # Remove extra whitespace
        text = " ".join(text.split())
        return text.strip()
        
    def _split_into_chunks(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[ProcessedChunk]:
        """Split text into overlapping chunks.
        
        Args:
            text: Text to split
            metadata: Metadata to attach to each chunk
            
        Returns:
            List[ProcessedChunk]: List of chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk with overlap
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            # Don't create tiny chunks at the end
            if len(chunk_text) < self.chunk_size // 2 and chunks:
                # Extend the last chunk instead
                last_chunk = chunks[-1]
                last_chunk.content += " " + chunk_text
                last_chunk.end_pos = start + len(chunk_text)
                break
            
            # Create chunk
            chunk = ProcessedChunk(
                content=chunk_text,
                metadata=metadata.copy(),
                start_pos=start,
                end_pos=start + len(chunk_text)
            )
            chunks.append(chunk)
            
            # Move start position, accounting for overlap
            start = end - self.chunk_overlap
            
        return chunks 