"""Markdown file processor."""
import re
from typing import List, Dict, Any
from pathlib import Path
import logging
from datetime import datetime

from .base_processor import BaseProcessor, ProcessedChunk

logger = logging.getLogger(__name__)

class MarkdownProcessor(BaseProcessor):
    """Processor for Markdown files."""
    
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the file."""
        return Path(file_path).suffix.lower() in ['.md', '.markdown']
        
    async def process(self, file_path: str) -> List[ProcessedChunk]:
        """Process a Markdown file into chunks."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            
            # Get file metadata
            metadata = self._extract_metadata(content, file_path)
            
            # Clean and preprocess content
            if not self.preserve_markdown:
                content = self._remove_markdown(content)
            content = self._preprocess_content(content)
            
            # Split into semantic chunks
            return self._split_into_semantic_chunks(content, metadata)
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            raise ValueError(f"Failed to process {file_path}: {e}")
            
    def _extract_metadata(
        self,
        content: str,
        file_path: Path
    ) -> Dict[str, Any]:
        """Extract metadata from file content and path."""
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "type": "markdown"
        }
        
        # Extract YAML frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if frontmatter_match:
            try:
                import yaml
                frontmatter = yaml.safe_load(frontmatter_match.group(1))
                if isinstance(frontmatter, dict):
                    metadata.update(frontmatter)
            except:
                logger.warning(f"Failed to parse frontmatter in {file_path}")
                
        return metadata
        
    def _remove_markdown(self, content: str) -> str:
        """Remove Markdown formatting while preserving content."""
        # Remove YAML frontmatter
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
        
        # Remove code blocks
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        content = re.sub(r'`.*?`', '', content)
        
        # Remove images and links
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        content = re.sub(r'\[([^\]]+)\]\(.*?\)', r'\1', content)
        
        # Remove headers
        content = re.sub(r'#{1,6}\s+', '', content)
        
        # Remove emphasis
        content = re.sub(r'[*_]{1,2}(.*?)[*_]{1,2}', r'\1', content)
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        return content
        
    def _preprocess_content(self, content: str) -> str:
        """Preprocess content for chunking."""
        # Remove YAML frontmatter if present
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
        
        # Normalize line endings
        content = content.replace('\r\n', '\n')
        
        # Add spacing around headers
        content = re.sub(r'(#{1,6}.*?)\n', r'\1\n\n', content)
        
        # Ensure proper spacing around lists
        content = re.sub(r'(\n[*-]\s+.*?\n)(?=[^*\n-])', r'\1\n', content)
        
        # Clean up extra whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        return content
        
    def _split_into_semantic_chunks(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[ProcessedChunk]:
        """Split content into semantic chunks."""
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Split into lines
        lines = content.split('\n')
        
        for line in lines:
            # Start new chunk on headers
            if re.match(r'^#{1,6}\s+', line):
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    chunks.extend(self._split_into_chunks(chunk_text, metadata))
                    current_chunk = []
                    current_length = 0
                    
            # Add line to current chunk
            current_chunk.append(line)
            current_length += len(line) + 1  # +1 for newline
            
            # Split if chunk is too large
            if current_length >= self.chunk_size:
                chunk_text = '\n'.join(current_chunk)
                chunks.extend(self._split_into_chunks(chunk_text, metadata))
                current_chunk = []
                current_length = 0
                
        # Handle remaining text
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.extend(self._split_into_chunks(chunk_text, metadata))
            
        return chunks 