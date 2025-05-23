"""Factory for creating file processors."""
from typing import List, Optional, Type
import logging

from .base_processor import BaseProcessor
from .markdown_processor import MarkdownProcessor
from .pdf_processor import PDFProcessor
from .word_processor import WordProcessor

logger = logging.getLogger(__name__)

class ProcessorFactory:
    """Factory for creating and managing file processors."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        preserve_markdown: bool = True
    ):
        """Initialize the processor factory.
        
        Args:
            chunk_size: Target size for text chunks
            chunk_overlap: Number of characters to overlap between chunks
            preserve_markdown: Whether to preserve markdown formatting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_markdown = preserve_markdown
        
        # Register default processors
        self.processors: List[BaseProcessor] = [
            MarkdownProcessor(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_markdown=preserve_markdown
            ),
            PDFProcessor(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            ),
            WordProcessor(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        ]
        
    def register_processor(self, processor_class: Type[BaseProcessor]):
        """Register a new processor type.
        
        Args:
            processor_class: Processor class to register
        """
        processor = processor_class(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            preserve_markdown=self.preserve_markdown
        )
        self.processors.append(processor)
        
    def get_processor(self, file_path: str) -> Optional[BaseProcessor]:
        """Get an appropriate processor for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            BaseProcessor: Processor instance or None if no suitable processor found
        """
        for processor in self.processors:
            if processor.can_process(file_path):
                return processor
        return None
        
    def can_process(self, file_path: str) -> bool:
        """Check if any processor can handle the file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if a suitable processor exists
        """
        return any(p.can_process(file_path) for p in self.processors)
        
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions.
        
        Returns:
            List[str]: List of supported extensions (e.g. ['.md', '.pdf'])
        """
        extensions = set()
        for processor in self.processors:
            # Call can_process with test paths
            for ext in ['.md', '.markdown', '.pdf', '.doc', '.docx']:
                if processor.can_process(f"test{ext}"):
                    extensions.add(ext)
        return sorted(list(extensions)) 