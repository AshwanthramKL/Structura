"""
Tests for the chunker module.
"""

import pytest
from unittest.mock import MagicMock

from src.pipeline.loader.doc_handle import DocHandle
from src.pipeline.chunker import TextChunker, Chunk


def test_text_chunker_initialization():
    """Test initializing a TextChunker."""
    chunker = TextChunker(chunk_size=5000, chunk_overlap=500)
    assert chunker.chunk_size == 5000
    assert chunker.chunk_overlap == 500
    assert chunker.include_metadata is True


def test_chunker_with_empty_text():
    """Test that an exception is raised when text is empty."""
    doc_handle = DocHandle(file_path="test.txt", content=b"", text="")
    chunker = TextChunker()
    
    with pytest.raises(ValueError, match="Document has no text content"):
        chunker.chunk(doc_handle)


def test_chunker_with_small_text():
    """Test chunking with a small text document that should produce one chunk."""
    text = "This is a short test document. It should produce one chunk."
    doc_handle = DocHandle(
        file_path="test.txt", 
        content=text.encode(), 
        text=text,
        metadata={"test_key": "test_value"}
    )
    
    chunker = TextChunker(chunk_size=1000)
    chunks = chunker.chunk(doc_handle)
    
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].index == 0
    assert chunks[0].total_chunks == 1
    assert "test_key" in chunks[0].metadata
    assert chunks[0].metadata["test_key"] == "test_value"


def test_chunker_with_medium_text():
    """Test chunking with a medium-sized text document that should produce multiple chunks."""
    # Create paragraphs of text to simulate a larger document
    paragraphs = []
    for i in range(10):
        paragraphs.append(f"Paragraph {i}: " + "This is sentence number one. " * 20)
    
    text = "\n\n".join(paragraphs)
    doc_handle = DocHandle(
        file_path="test.txt", 
        content=text.encode(), 
        text=text
    )
    
    # Use a much smaller chunk size to ensure multiple chunks
    chunker = TextChunker(chunk_size=200, chunk_overlap=50)
    chunks = chunker.chunk(doc_handle)
    
    # Should produce multiple chunks
    assert len(chunks) > 1
    
    # All chunks should have the correct metadata
    for i, chunk in enumerate(chunks):
        assert chunk.index == i
        assert chunk.total_chunks == len(chunks)
        assert "file_path" in chunk.metadata
        assert chunk.metadata["file_path"] == "test.txt"
        assert "chunk_index" in chunk.metadata
        assert chunk.metadata["chunk_index"] == i


def test_chunker_metadata_inclusion():
    """Test that document metadata is included in chunks when specified."""
    text = "This is a test document with metadata."
    doc_handle = DocHandle(
        file_path="test.txt", 
        content=text.encode(), 
        text=text,
        metadata={"source": "test", "author": "tester"}
    )
    
    # Test with metadata included
    chunker_with_metadata = TextChunker(include_metadata=True)
    chunks_with_metadata = chunker_with_metadata.chunk(doc_handle)
    
    assert chunks_with_metadata[0].metadata["source"] == "test"
    assert chunks_with_metadata[0].metadata["author"] == "tester"
    
    # Test with metadata excluded
    chunker_without_metadata = TextChunker(include_metadata=False)
    chunks_without_metadata = chunker_without_metadata.chunk(doc_handle)
    
    assert "source" not in chunks_without_metadata[0].metadata
    assert "author" not in chunks_without_metadata[0].metadata
    assert "file_path" in chunks_without_metadata[0].metadata  # Still includes chunk-specific metadata 