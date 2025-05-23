"""Text chunking strategies for RAG."""
from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass

@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    content: str
    metadata: Dict[str, Any]
    start_char: int
    end_char: int

class ChunkingStrategy:
    """Base class for chunking strategies."""
    
    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any],
        min_chunk_size: int = 100,
        max_chunk_size: int = 512,
        overlap: int = 50
    ) -> List[Chunk]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach to chunks
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of chunks with metadata
        """
        raise NotImplementedError

class MarkdownChunker(ChunkingStrategy):
    """Chunks text while preserving markdown structure."""
    
    def chunk_text(
        self,
        text: str,
        metadata: dict,
        min_chunk_size: int = 100,
        max_chunk_size: int = 512,
        overlap: int = 50
    ) -> List[Chunk]:
        """Chunk text while preserving markdown structure."""
        if not text:
            return []
            
        # Split text into lines
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0
        start_pos = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            # If line is too long, split it
            if line_size > max_chunk_size:
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(Chunk(
                        content=chunk_text,
                        metadata=metadata.copy(),
                        start_char=start_pos,
                        end_char=start_pos + len(chunk_text)
                    ))
                    start_pos += len(chunk_text) + 1
                    current_chunk = []
                    current_size = 0
                
                # Split long line into smaller chunks
                words = line.split()
                current_line = []
                current_line_size = 0
                
                for word in words:
                    word_size = len(word) + 1  # +1 for space
                    if current_line_size + word_size > max_chunk_size:
                        if current_line:
                            line_text = " ".join(current_line)
                            chunks.append(Chunk(
                                content=line_text,
                                metadata=metadata.copy(),
                                start_char=start_pos,
                                end_char=start_pos + len(line_text)
                            ))
                            start_pos += len(line_text) + 1
                            current_line = []
                            current_line_size = 0
                            
                        # Handle words longer than max_chunk_size
                        if word_size > max_chunk_size:
                            for i in range(0, len(word), max_chunk_size):
                                word_chunk = word[i:i+max_chunk_size]
                                chunks.append(Chunk(
                                    content=word_chunk,
                                    metadata=metadata.copy(),
                                    start_char=start_pos,
                                    end_char=start_pos + len(word_chunk)
                                ))
                                start_pos += len(word_chunk)
                        else:
                            current_line.append(word)
                            current_line_size = word_size
                    else:
                        current_line.append(word)
                        current_line_size += word_size
                
                if current_line:
                    line_text = " ".join(current_line)
                    chunks.append(Chunk(
                        content=line_text,
                        metadata=metadata.copy(),
                        start_char=start_pos,
                        end_char=start_pos + len(line_text)
                    ))
                    start_pos += len(line_text) + 1
            
            # If adding this line would exceed max size, create new chunk
            elif current_size + line_size > max_chunk_size and current_chunk:
                chunk_text = "\n".join(current_chunk)
                chunks.append(Chunk(
                    content=chunk_text,
                    metadata=metadata.copy(),
                    start_char=start_pos,
                    end_char=start_pos + len(chunk_text)
                ))
                start_pos += len(chunk_text) + 1
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(Chunk(
                content=chunk_text,
                metadata=metadata.copy(),
                start_char=start_pos,
                end_char=start_pos + len(chunk_text)
            ))
        
        return chunks

class SentenceChunker(ChunkingStrategy):
    """Chunks text by sentences."""
    
    def chunk_text(
        self,
        text: str,
        metadata: dict,
        min_chunk_size: int = 100,
        max_chunk_size: int = 512,
        overlap: int = 50
    ) -> List[Chunk]:
        """Chunk text into sentences."""
        if not text:
            return []
            
        # Split text into sentences
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        chunks = []
        current_chunk = []
        current_size = 0
        start_pos = 0
        
        for sentence in sentences:
            sentence_size = len(sentence) + 2  # +2 for ". "
            
            # If sentence is too long, split it
            if sentence_size > max_chunk_size:
                if current_chunk:
                    chunk_text = ". ".join(current_chunk) + "."
                    chunks.append(Chunk(
                        content=chunk_text,
                        metadata=metadata.copy(),
                        start_char=start_pos,
                        end_char=start_pos + len(chunk_text)
                    ))
                    start_pos += len(chunk_text) + 1
                    current_chunk = []
                    current_size = 0
                
                # Split long sentence into smaller chunks
                words = sentence.split()
                current_sentence = []
                current_sentence_size = 0
                
                for word in words:
                    word_size = len(word) + 1  # +1 for space
                    if current_sentence_size + word_size > max_chunk_size:
                        if current_sentence:
                            sentence_text = " ".join(current_sentence) + "."
                            chunks.append(Chunk(
                                content=sentence_text,
                                metadata=metadata.copy(),
                                start_char=start_pos,
                                end_char=start_pos + len(sentence_text)
                            ))
                            start_pos += len(sentence_text) + 1
                            current_sentence = []
                            current_sentence_size = 0
                            
                        # Handle words longer than max_chunk_size
                        if word_size > max_chunk_size:
                            for i in range(0, len(word), max_chunk_size):
                                word_chunk = word[i:i+max_chunk_size]
                                chunks.append(Chunk(
                                    content=word_chunk,
                                    metadata=metadata.copy(),
                                    start_char=start_pos,
                                    end_char=start_pos + len(word_chunk)
                                ))
                                start_pos += len(word_chunk)
                        else:
                            current_sentence.append(word)
                            current_sentence_size = word_size
                    else:
                        current_sentence.append(word)
                        current_sentence_size += word_size
                
                if current_sentence:
                    sentence_text = " ".join(current_sentence) + "."
                    chunks.append(Chunk(
                        content=sentence_text,
                        metadata=metadata.copy(),
                        start_char=start_pos,
                        end_char=start_pos + len(sentence_text)
                    ))
                    start_pos += len(sentence_text) + 1
            
            # If adding this sentence would exceed max size, create new chunk
            elif current_size + sentence_size > max_chunk_size and current_chunk:
                chunk_text = ". ".join(current_chunk) + "."
                chunks.append(Chunk(
                    content=chunk_text,
                    metadata=metadata.copy(),
                    start_char=start_pos,
                    end_char=start_pos + len(chunk_text)
                ))
                start_pos += len(chunk_text) + 1
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = ". ".join(current_chunk) + "."
            chunks.append(Chunk(
                content=chunk_text,
                metadata=metadata.copy(),
                start_char=start_pos,
                end_char=start_pos + len(chunk_text)
            ))
        
        return chunks

class ChunkingConfig:
    """Configuration for text chunking."""
    
    def __init__(
        self,
        strategy: str = "markdown",
        min_chunk_size: int = 100,
        max_chunk_size: int = 512,
        overlap: int = 50
    ):
        """
        Initialize chunking configuration.
        
        Args:
            strategy: Chunking strategy ("markdown" or "sentence")
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters
            overlap: Number of characters to overlap between chunks
        """
        self.strategy = strategy
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
        self._strategies = {
            "markdown": MarkdownChunker(),
            "sentence": SentenceChunker()
        }
    
    def get_chunker(self) -> ChunkingStrategy:
        """Get the configured chunking strategy."""
        if self.strategy not in self._strategies:
            raise ValueError(f"Unknown chunking strategy: {self.strategy}")
        return self._strategies[self.strategy] 