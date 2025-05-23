"""Tests for file processor."""
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.processors.file_processor import FileProcessor
from src.processors.chunking import MarkdownChunker

# Test data
MARKDOWN_CONTENT = """# Test Document

This is a test markdown document.

## Section 1

Some content here.

## Section 2

More content here."""

TEXT_CONTENT = """This is a test text file.
It has multiple lines.
And some more content."""

@pytest.fixture
def processor():
    """Create file processor for testing."""
    return FileProcessor(chunking_strategy=MarkdownChunker())

@pytest.fixture
def test_files(tmp_path):
    """Create test files."""
    # Create test files
    test_dir = tmp_path
    
    # Empty file
    empty_file = test_dir / "empty.txt"
    empty_file.touch()
    
    # Markdown file
    md_file = test_dir / "test.md"
    md_file.write_text("# Test\nThis is a test markdown file.\n\nWith multiple paragraphs.")
    
    # Text file
    txt_file = test_dir / "test.txt"
    txt_file.write_text("This is a test text file.\nWith multiple lines.")
    
    return {
        'empty': str(empty_file),
        'markdown': str(md_file),
        'text': str(txt_file)
    }

def test_process_markdown(processor, test_files):
    """Test processing markdown files."""
    chunks = processor.process_file(test_files['markdown'])
    
    assert len(chunks) > 0
    assert all(isinstance(c.content, str) for c in chunks)
    assert all(c.metadata['type'] == 'markdown' for c in chunks)
    assert all(c.metadata['source'] == test_files['markdown'] for c in chunks)

def test_process_text(processor, test_files):
    """Test processing text files."""
    chunks = processor.process_file(test_files['text'])
    
    assert len(chunks) > 0
    assert all(isinstance(c.content, str) for c in chunks)
    assert all(c.metadata['type'] == 'text' for c in chunks)
    assert all(c.metadata['source'] == test_files['text'] for c in chunks)

@patch('src.processors.file_processor.Document')
def test_process_docx(mock_document, processor, tmp_path):
    """Test processing Word documents."""
    # Mock Document class
    mock_doc = Mock()
    mock_doc.paragraphs = [
        Mock(text="Paragraph 1"),
        Mock(text="Paragraph 2"),
        Mock(text="Paragraph 3")
    ]
    mock_document.return_value = mock_doc
    
    # Create dummy docx file
    docx_file = tmp_path / "test.docx"
    docx_file.touch()
    
    chunks = processor.process_file(str(docx_file))
    
    assert len(chunks) > 0
    assert all(isinstance(c.content, str) for c in chunks)
    assert all(c.metadata['type'] == 'docx' for c in chunks)
    assert all(c.metadata['source'] == str(docx_file) for c in chunks)

@patch('src.processors.file_processor.Presentation')
def test_process_pptx(mock_presentation, processor, tmp_path):
    """Test processing PowerPoint presentations."""
    # Mock Presentation class
    mock_pres = Mock()
    mock_shape1 = Mock()
    mock_shape1.text = "Slide 1 content"
    mock_shape2 = Mock()
    mock_shape2.text = "Slide 2 content"
    
    mock_slide1 = Mock()
    mock_slide1.shapes = [mock_shape1]
    mock_slide2 = Mock()
    mock_slide2.shapes = [mock_shape2]
    
    mock_pres.slides = [mock_slide1, mock_slide2]
    mock_presentation.return_value = mock_pres
    
    # Create dummy pptx file
    pptx_file = tmp_path / "test.pptx"
    pptx_file.touch()
    
    chunks = processor.process_file(str(pptx_file))
    
    assert len(chunks) > 0
    assert all(isinstance(c.content, str) for c in chunks)
    assert all(c.metadata['type'] == 'pptx' for c in chunks)
    assert all(c.metadata['source'] == str(pptx_file) for c in chunks)

@patch('src.processors.file_processor.PdfReader')
def test_process_pdf(mock_pdfreader, processor, tmp_path):
    """Test processing PDF documents."""
    # Mock PdfReader class
    mock_reader = Mock()
    mock_page1 = Mock()
    mock_page1.extract_text.return_value = "Page 1 content"
    mock_page2 = Mock()
    mock_page2.extract_text.return_value = "Page 2 content"
    
    mock_reader.pages = [mock_page1, mock_page2]
    mock_pdfreader.return_value = mock_reader
    
    # Create dummy pdf file
    pdf_file = tmp_path / "test.pdf"
    pdf_file.touch()
    
    chunks = processor.process_file(str(pdf_file))
    
    assert len(chunks) > 0
    assert all(isinstance(c.content, str) for c in chunks)
    assert all(c.metadata['type'] == 'pdf' for c in chunks)
    assert all(c.metadata['source'] == str(pdf_file) for c in chunks)

def test_custom_chunking_config(tmp_path):
    """Test custom chunking configuration."""
    # Create processor with custom chunking strategy
    processor = FileProcessor(chunking_strategy=MarkdownChunker())
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("A " * 300)  # Create content larger than chunk size
    
    chunks = processor.process_file(str(test_file))
    
    assert len(chunks) > 1  # Should be split into multiple chunks
    assert all(isinstance(c.content, str) for c in chunks)
    assert all(c.metadata['type'] == 'text' for c in chunks)
    assert all(c.metadata['source'] == str(test_file) for c in chunks)

def test_empty_file(processor, test_files):
    """Test processing empty files."""
    chunks = processor.process_file(test_files['empty'])
    assert len(chunks) == 0

def test_invalid_file(processor):
    """Test processing invalid files."""
    chunks = processor.process_file("nonexistent.txt")
    assert len(chunks) == 0

def test_unsupported_extension(processor, tmp_path):
    """Test processing files with unsupported extensions."""
    unsupported_file = tmp_path / "test.xyz"
    unsupported_file.touch()
    
    chunks = processor.process_file(str(unsupported_file))
    assert len(chunks) == 0 