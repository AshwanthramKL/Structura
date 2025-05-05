"""
Text chunker implementation using LlamaIndex's SemanticTextSplitter.

This chunker is used for splitting text documents that exceed the context window,
as determined by the Planner. It uses semantic chunking to preserve meaning
across chunk boundaries.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode, Document

from src.pipeline.loader.doc_handle import DocHandle


@dataclass
class Chunk:
    """
    Represents a chunk of text or images with associated metadata.
    
    Attributes:
        text: The text content of the chunk (for text documents)
        images: List of image data for PDF pages (for PDF documents)
        metadata: Additional metadata about the chunk
        index: Position of this chunk in the sequence
        total_chunks: Total number of chunks in the document
    """
    text: Optional[str] = None
    images: Optional[List[bytes]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    index: int = 0
    total_chunks: int = 1
    
    def __post_init__(self):
        """Validate that either text or images is provided."""
        if self.text is None and self.images is None:
            raise ValueError("Either text or images must be provided for a Chunk")


class TextChunker:
    """
    Chunks text documents using LlamaIndex's sentence splitter.
    
    This implementation focuses on creating logical chunks based on sentences,
    which is better for extraction tasks than naive chunking strategies.
    """
    
    def __init__(
        self,
        chunk_size: int = 3000,
        chunk_overlap: int = 200, 
        include_metadata: bool = True
    ):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            include_metadata: Whether to include document metadata in chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.include_metadata = include_metadata
        
        # Initialize the sentence splitter
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    
    def chunk(self, doc_handle: DocHandle) -> List[Chunk]:
        """
        Split a document into semantic chunks.
        
        Args:
            doc_handle: Document handle containing text content
            
        Returns:
            List of Chunk objects
        """
        if not doc_handle.text:
            raise ValueError("Document has no text content to chunk")
        
        # Create a Document from the document text
        document = Document(text=doc_handle.text)
        
        # Use the splitter to split the text
        nodes = self.splitter.get_nodes_from_documents([document])
        
        # Create Chunk objects from the nodes
        chunks = []
        for i, node in enumerate(nodes):
            # Create metadata by combining document metadata with chunk metadata
            metadata = {}
            
            if self.include_metadata:
                metadata.update(doc_handle.metadata)
            
            # Add chunk-specific metadata
            metadata.update({
                "file_path": doc_handle.file_path,
                "mime_type": doc_handle.mime_type,
                "chunk_index": i,
            })
            
            # Create the chunk
            chunk = Chunk(
                text=node.get_content(),
                metadata=metadata,
                index=i,
                total_chunks=len(nodes)
            )
            chunks.append(chunk)
        
        return chunks
