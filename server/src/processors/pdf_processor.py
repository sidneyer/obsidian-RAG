"""PDF file processor."""
import re
from typing import List, Dict, Any
from pathlib import Path
import logging
from datetime import datetime
import fitz  # PyMuPDF

from .base_processor import BaseProcessor, ProcessedChunk

logger = logging.getLogger(__name__)

class PDFProcessor(BaseProcessor):
    """Processor for PDF files."""
    
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the file."""
        return Path(file_path).suffix.lower() == '.pdf'
        
    async def process(self, file_path: str) -> List[ProcessedChunk]:
        """Process a PDF file into chunks."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            # Open PDF
            doc = fitz.open(file_path)
            
            # Get document metadata
            metadata = self._extract_metadata(doc, file_path)
            
            chunks = []
            current_chunk = []
            current_length = 0
            
            # Process each page
            for page_num, page in enumerate(doc):
                # Extract text with formatting
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" not in block:
                        continue
                        
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if not text:
                                continue
                                
                            # Handle font properties
                            font_properties = {
                                "size": span["size"],
                                "font": span["font"],
                                "is_bold": "bold" in span["font"].lower(),
                                "is_italic": "italic" in span["font"].lower()
                            }
                            
                            # Start new chunk for headers (large or bold text)
                            is_header = (
                                font_properties["size"] > 12 or
                                font_properties["is_bold"]
                            )
                            
                            if is_header and current_chunk:
                                chunk_text = " ".join(current_chunk)
                                if len(chunk_text) >= self.chunk_size // 2:
                                    chunk_metadata = metadata.copy()
                                    chunk_metadata.update({
                                        "page": page_num + 1,
                                        "position": len(chunks)
                                    })
                                    chunks.extend(
                                        self._split_into_chunks(chunk_text, chunk_metadata)
                                    )
                                current_chunk = []
                                current_length = 0
                                
                            # Add text to current chunk
                            current_chunk.append(text)
                            current_length += len(text) + 1
                            
                            # Split if chunk is too large
                            if current_length >= self.chunk_size:
                                chunk_text = " ".join(current_chunk)
                                chunk_metadata = metadata.copy()
                                chunk_metadata.update({
                                    "page": page_num + 1,
                                    "position": len(chunks)
                                })
                                chunks.extend(
                                    self._split_into_chunks(chunk_text, chunk_metadata)
                                )
                                current_chunk = []
                                current_length = 0
                                
                # Force chunk break at page boundaries
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    if len(chunk_text) >= self.chunk_size // 2:
                        chunk_metadata = metadata.copy()
                        chunk_metadata.update({
                            "page": page_num + 1,
                            "position": len(chunks)
                        })
                        chunks.extend(
                            self._split_into_chunks(chunk_text, chunk_metadata)
                        )
                    current_chunk = []
                    current_length = 0
                    
            # Handle any remaining text
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.chunk_size // 2:
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "page": doc.page_count,
                        "position": len(chunks)
                    })
                    chunks.extend(
                        self._split_into_chunks(chunk_text, chunk_metadata)
                    )
                    
            doc.close()
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            raise ValueError(f"Failed to process {file_path}: {e}")
            
    def _extract_metadata(
        self,
        doc: fitz.Document,
        file_path: Path
    ) -> Dict[str, Any]:
        """Extract metadata from PDF document."""
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "type": "pdf",
            "pages": doc.page_count
        }
        
        # Extract PDF metadata
        pdf_metadata = doc.metadata
        if pdf_metadata:
            if pdf_metadata.get("title"):
                metadata["title"] = pdf_metadata["title"]
            if pdf_metadata.get("author"):
                metadata["author"] = pdf_metadata["author"]
            if pdf_metadata.get("subject"):
                metadata["subject"] = pdf_metadata["subject"]
            if pdf_metadata.get("keywords"):
                metadata["keywords"] = pdf_metadata["keywords"]
                
        return metadata 