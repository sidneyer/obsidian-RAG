"""Tests for chunking strategies."""
import pytest
import os
from src.chunking import MarkdownChunker, SentenceChunker

@pytest.fixture
def markdown_chunker():
    """Create a markdown chunker with test settings."""
    os.environ["RAG_CHUNK_SIZE"] = "100"
    os.environ["RAG_CHUNK_OVERLAP"] = "20"
    os.environ["RAG_PRESERVE_MARKDOWN"] = "1"
    return MarkdownChunker()

@pytest.fixture
def sentence_chunker():
    """Create a sentence chunker with test settings."""
    os.environ["RAG_CHUNK_SIZE"] = "100"
    os.environ["RAG_CHUNK_OVERLAP"] = "20"
    return SentenceChunker()

def test_markdown_chunker_headers(markdown_chunker):
    """Test markdown chunking with headers."""
    text = """# Header 1
This is paragraph 1.
## Header 2
This is paragraph 2.
### Header 3
This is paragraph 3."""
    
    chunks = markdown_chunker.chunk(text)
    assert len(chunks) == 6  # Each header and paragraph is a separate chunk
    assert chunks[0]["text"] == "# Header 1"
    assert "paragraph 1" in chunks[1]["text"]
    assert chunks[2]["text"] == "## Header 2"
    assert "paragraph 2" in chunks[3]["text"]
    assert chunks[4]["text"] == "### Header 3"
    assert "paragraph 3" in chunks[5]["text"]

def test_markdown_chunker_long_paragraphs(markdown_chunker):
    """Test markdown chunking with long paragraphs."""
    text = "This is a very long paragraph that should be split into multiple chunks. " * 5
    
    chunks = markdown_chunker.chunk(text)
    assert len(chunks) > 1
    assert all(chunk["length"] <= int(os.getenv("RAG_CHUNK_SIZE")) for chunk in chunks)

def test_markdown_chunker_overlap(markdown_chunker):
    """Test markdown chunking with overlap."""
    # Create a long paragraph that will be split into multiple chunks
    text = "This is a very long paragraph that should be split into multiple chunks. " * 5
    
    chunks = markdown_chunker.chunk(text)
    assert len(chunks) > 1
    
    # Check for overlap between consecutive chunks
    for i in range(len(chunks) - 1):
        words_in_first = set(chunks[i]["text"].split())
        words_in_second = set(chunks[i + 1]["text"].split())
        overlap = words_in_first & words_in_second
        assert len(overlap) > 0, f"No overlap found between chunks {i} and {i+1}"

def test_sentence_chunker_basic(sentence_chunker):
    """Test basic sentence chunking."""
    text = "This is sentence one. This is sentence two! This is sentence three?"
    
    chunks = sentence_chunker.chunk(text)
    assert len(chunks) == 1
    assert "sentence one" in chunks[0]["text"]
    assert "sentence two" in chunks[0]["text"]
    assert "sentence three" in chunks[0]["text"]

def test_sentence_chunker_long_text(sentence_chunker):
    """Test sentence chunking with long text."""
    text = "This is a test sentence. " * 20
    
    chunks = sentence_chunker.chunk(text)
    assert len(chunks) > 1
    assert all(chunk["length"] <= int(os.getenv("RAG_CHUNK_SIZE")) for chunk in chunks)

def test_sentence_chunker_overlap(sentence_chunker):
    """Test sentence chunking with overlap."""
    text = ("First sentence. Second sentence. Third sentence. " * 5)
    
    chunks = sentence_chunker.chunk(text)
    assert len(chunks) > 1
    # Check for overlap
    first_chunk_sentences = set(chunks[0]["text"].split('.'))
    second_chunk_sentences = set(chunks[1]["text"].split('.'))
    assert len(first_chunk_sentences & second_chunk_sentences) > 0

def test_empty_input():
    """Test both chunkers with empty input."""
    markdown_chunker = MarkdownChunker()
    sentence_chunker = SentenceChunker()
    
    assert len(markdown_chunker.chunk("")) == 0
    assert len(sentence_chunker.chunk("")) == 0

def test_single_line():
    """Test both chunkers with single line input."""
    markdown_chunker = MarkdownChunker()
    sentence_chunker = SentenceChunker()
    
    text = "This is a single line."
    
    markdown_chunks = markdown_chunker.chunk(text)
    sentence_chunks = sentence_chunker.chunk(text)
    
    assert len(markdown_chunks) == 1
    assert len(sentence_chunks) == 1
    assert markdown_chunks[0]["text"] == text.strip()
    assert sentence_chunks[0]["text"] == text.strip()

def test_chunker_configuration():
    """Test chunker configuration through environment variables."""
    os.environ["RAG_CHUNK_SIZE"] = "200"
    os.environ["RAG_CHUNK_OVERLAP"] = "40"
    
    markdown_chunker = MarkdownChunker()
    sentence_chunker = SentenceChunker()
    
    assert markdown_chunker.chunk_size == 200
    assert markdown_chunker.chunk_overlap == 40
    assert sentence_chunker.chunk_size == 200
    assert sentence_chunker.chunk_overlap == 40 