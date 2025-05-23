from abc import ABC, abstractmethod
from typing import List, Dict, Any
import re
import os

class ChunkingStrategy(ABC):
    def __init__(self):
        self.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "500"))
        self.chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))
        
    @abstractmethod
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata."""
        pass
        
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

class MarkdownChunker(ChunkingStrategy):
    def __init__(self):
        super().__init__()
        self.preserve_markdown = os.getenv("RAG_PRESERVE_MARKDOWN", "1") == "1"
        
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """Split markdown text into semantic chunks."""
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Split into lines and paragraphs
        paragraphs = []
        current_paragraph = []
        
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('#'):  # Headers start new paragraphs
                if current_paragraph:
                    paragraphs.append('\n'.join(current_paragraph))
                    current_paragraph = []
                paragraphs.append(line)  # Add header as its own paragraph
            elif not line:  # Empty lines end paragraphs
                if current_paragraph:
                    paragraphs.append('\n'.join(current_paragraph))
                    current_paragraph = []
            else:
                current_paragraph.append(line)
        
        if current_paragraph:
            paragraphs.append('\n'.join(current_paragraph))
        
        for paragraph in paragraphs:
            is_header = paragraph.startswith('#')
            paragraph_length = len(paragraph)
            
            # Start new chunk if:
            # 1. Current chunk would exceed max size
            # 2. Current paragraph is a header
            # 3. Previous paragraph was a header
            if (current_length + paragraph_length > self.chunk_size and current_chunk) or \
               is_header or \
               (current_chunk and current_chunk[-1].startswith('#')):
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append({
                        "text": self._clean_text(chunk_text),
                        "length": current_length
                    })
                
                # Start new chunk with overlap if not a header
                if not is_header and len(current_chunk) > 1:
                    # Keep last non-header paragraph for overlap
                    for p in reversed(current_chunk):
                        if not p.startswith('#'):
                            current_chunk = [p]
                            current_length = len(p)
                            break
                    else:
                        current_chunk = []
                        current_length = 0
                else:
                    current_chunk = []
                    current_length = 0
            
            # Handle long paragraphs that exceed chunk size
            if paragraph_length > self.chunk_size:
                words = paragraph.split()
                current_part = []
                current_part_length = 0
                
                for word in words:
                    word_length = len(word) + 1  # +1 for space
                    if current_part_length + word_length > self.chunk_size and current_part:
                        part_text = ' '.join(current_part)
                        chunks.append({
                            "text": self._clean_text(part_text),
                            "length": current_part_length
                        })
                        # Keep some overlap
                        overlap_words = current_part[-3:]  # Keep last 3 words for context
                        current_part = overlap_words + [word]
                        current_part_length = sum(len(w) + 1 for w in current_part)
                    else:
                        current_part.append(word)
                        current_part_length += word_length
                
                if current_part:
                    current_chunk = [' '.join(current_part)]
                    current_length = current_part_length
            else:
                current_chunk.append(paragraph)
                current_length += paragraph_length
        
        # Add final chunk if not empty
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                "text": self._clean_text(chunk_text),
                "length": current_length
            })
        
        return chunks

class SentenceChunker(ChunkingStrategy):
    def __init__(self):
        super().__init__()
        self.sentence_end = r'[.!?][\s]{1,2}'
        
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """Split text into chunks at sentence boundaries."""
        chunks = []
        sentences = re.split(self.sentence_end, text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "text": self._clean_text(chunk_text),
                    "length": current_length
                })
                
                # Start new chunk with overlap
                overlap_sentences = []
                overlap_length = 0
                
                for s in reversed(current_chunk):
                    if overlap_length + len(s) > self.chunk_overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_length += len(s)
                    
                current_chunk = overlap_sentences
                current_length = overlap_length
                
            current_chunk.append(sentence)
            current_length += sentence_length
            
        # Add final chunk if not empty
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "text": self._clean_text(chunk_text),
                "length": current_length
            })
            
        return chunks 