import os
import mimetypes
from typing import Dict, Any, Optional, BinaryIO, TextIO, Union
from abc import ABC, abstractmethod

from src.pipeline.loader.doc_handle import DocHandle

class BaseFileLoader(ABC):
    """Abstract base class for all file loaders"""
    
    @classmethod
    def initialize(cls):
        """Initialize the loader by registering custom MIME types."""
        # Register additional MIME types
        mimetypes.add_type('application/x-bibtex', '.bib')
        mimetypes.add_type('text/markdown', '.md')
        mimetypes.add_type('text/csv', '.csv')
    
    @classmethod
    @abstractmethod
    def load_file(cls, file_path: str) -> DocHandle:
        """Load a file from disk into a DocHandle."""
        raise NotImplementedError()
    
    @classmethod
    @abstractmethod
    def load_from_stream(
        cls,
        stream: Union[BinaryIO, TextIO],
        file_name: str,
        mime_type: Optional[str] = None
    ) -> DocHandle:
        """Load a file from a stream into a DocHandle."""
        raise NotImplementedError()
    
    @classmethod
    def get_basic_metadata(cls, file_path: str) -> Dict[str, str]:
        """Get basic metadata common to all file types."""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        return {
            "extension": ext,
            "filename": os.path.basename(file_path)
        } 