"""Tests for text chunking strategies."""
import pytest
from src.processors.chunking import (
    ChunkingConfig,
    MarkdownChunker,
    SentenceChunker,
    Chunk
)

# Test data
MARKDOWN_TEXT = """# Title

This is a paragraph with some content.

## Section 1

This is the first section with multiple
lines of content that should be kept
together as a single chunk.

### Subsection 1.1

More content here that explains
the details of this subsection.

## Section 2

Final section with some concluding
remarks about the topic."""

PROSE_TEXT = """This is a test sentence. Here is another one! And a third one?
This is a new paragraph with multiple sentences. It continues here.
And here is the final sentence of this text sample."""

@pytest.fixture
def markdown_chunker():
    return MarkdownChunker()

@pytest.fixture
def sentence_chunker():
    return SentenceChunker()

@pytest.fixture
def basic_metadata():
    return {"source": "test.md", "type": "markdown"}

def test_markdown_chunker_basic(markdown_chunker, basic_metadata):
    chunks = markdown_chunker.chunk_text(
        MARKDOWN_TEXT,
        basic_metadata,
        max_chunk_size=200
    )
    
    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(len(c.content) <= 200 for c in chunks)
    assert all(c.metadata == basic_metadata for c in chunks)

def test_markdown_chunker_preserves_headers(markdown_chunker, basic_metadata):
    chunks = markdown_chunker.chunk_text(
        MARKDOWN_TEXT,
        basic_metadata
    )
    
    # Check if headers are preserved at chunk boundaries
    headers_found = False
    for chunk in chunks:
        if any(line.startswith('#') for line in chunk.content.split('\n')):
            headers_found = True
            break
    
    assert headers_found

def test_sentence_chunker_basic(sentence_chunker, basic_metadata):
    chunks = sentence_chunker.chunk_text(
        PROSE_TEXT,
        basic_metadata,
        max_chunk_size=100
    )
    
    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(len(c.content) <= 100 for c in chunks)
    assert all(c.metadata == basic_metadata for c in chunks)

def test_sentence_chunker_preserves_sentences(sentence_chunker, basic_metadata):
    chunks = sentence_chunker.chunk_text(
        PROSE_TEXT,
        basic_metadata,
        max_chunk_size=1000  # Large size to keep all sentences together
    )
    
    # Count sentences in original text and chunks
    original_sentences = len([s for s in PROSE_TEXT.split('.') if s.strip()])
    chunk_sentences = sum(
        len([s for s in c.content.split('.') if s.strip()])
        for c in chunks
    )
    
    assert chunk_sentences >= original_sentences

def test_chunking_config():
    config = ChunkingConfig(
        strategy="markdown",
        min_chunk_size=100,
        max_chunk_size=500,
        overlap=50
    )
    
    chunker = config.get_chunker()
    assert isinstance(chunker, MarkdownChunker)
    
    config.strategy = "sentence"
    chunker = config.get_chunker()
    assert isinstance(chunker, SentenceChunker)
    
    with pytest.raises(ValueError):
        config.strategy = "invalid"
        config.get_chunker()

def test_chunk_metadata_preservation(markdown_chunker):
    metadata = {
        "source": "test.md",
        "type": "markdown",
        "author": "Test Author",
        "tags": ["test", "example"]
    }
    
    chunks = markdown_chunker.chunk_text(
        MARKDOWN_TEXT,
        metadata
    )
    
    assert all(c.metadata == metadata for c in chunks)
    assert all("author" in c.metadata for c in chunks)
    assert all("tags" in c.metadata for c in chunks)

def test_chunk_position_tracking(markdown_chunker, basic_metadata):
    chunks = markdown_chunker.chunk_text(
        MARKDOWN_TEXT,
        basic_metadata
    )
    
    # Check that chunk positions are sequential
    for i in range(len(chunks) - 1):
        assert chunks[i].end_char == chunks[i + 1].start_char

def test_empty_text(markdown_chunker, sentence_chunker, basic_metadata):
    # Test both chunkers with empty text
    md_chunks = markdown_chunker.chunk_text("", basic_metadata)
    sent_chunks = sentence_chunker.chunk_text("", basic_metadata)
    
    assert len(md_chunks) == 0
    assert len(sent_chunks) == 0

def test_single_long_word(sentence_chunker, basic_metadata):
    # Test handling of words longer than max_chunk_size
    long_word = "a" * 1000
    chunks = sentence_chunker.chunk_text(
        long_word,
        basic_metadata,
        max_chunk_size=100
    )
    
    assert len(chunks) > 0
    assert all(len(c.content) <= 100 for c in chunks)

def test_markdown_list_handling(markdown_chunker, basic_metadata):
    list_text = """# List Test

- Item 1
- Item 2
  - Subitem 2.1
  - Subitem 2.2
- Item 3

More text here."""

    chunks = markdown_chunker.chunk_text(
        list_text,
        basic_metadata
    )
    
    # Check if list structure is preserved in at least one chunk
    list_preserved = False
    for chunk in chunks:
        if "- Item" in chunk.content:
            list_preserved = True
            break
    
    assert list_preserved 