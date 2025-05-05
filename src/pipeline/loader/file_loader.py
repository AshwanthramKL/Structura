import os
import mimetypes
from typing import Dict, Any, Optional, BinaryIO, TextIO, Union, Type

from src.pipeline.loader.doc_handle import DocHandle
from src.pipeline.loader.base_loader import BaseFileLoader
from src.pipeline.loader.text_loader import TextFileLoader, CSVLoader, JSONLoader
from src.pipeline.loader.pdf_loader import PDFLoader
from src.pipeline.loader.binary_loader import BinaryFileLoader

class FileLoader:
    """
    Factory class that selects and uses the appropriate loader for different file types.
    Provides a unified interface to load various file formats while delegating to specialized loaders.
    """
    
    @classmethod
    def initialize(cls):
        """
        Initialize the FileLoader by registering custom MIME types.
        Call this before using the FileLoader class.
        """
        # Initialize the base loader which registers MIME types
        BaseFileLoader.initialize()
    
    @classmethod
    def get_loader_for_file(cls, file_path: str) -> Type[BaseFileLoader]:
        """
        Get the appropriate loader class for a file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            The appropriate loader class
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == ".pdf":
            return PDFLoader
        elif ext == ".csv":
            return CSVLoader
        elif ext == ".json":
            return JSONLoader
        elif ext in [".txt", ".md", ".bib"]:
            return TextFileLoader
        else:
            return BinaryFileLoader
    
    @classmethod
    def load_file(cls, file_path: str) -> DocHandle:
        """
        Load a file from disk using the appropriate loader.
        
        Args:
            file_path: Path to the file on disk
            
        Returns:
            DocHandle: Normalized file handle with content and metadata
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        # Get the appropriate loader
        loader_class = cls.get_loader_for_file(file_path)
        
        # Use the loader to load the file
        return loader_class.load_file(file_path)
    
    @classmethod
    def load_from_stream(
        cls,
        stream: Union[BinaryIO, TextIO],
        file_name: str,
        mime_type: Optional[str] = None
    ) -> DocHandle:
        """
        Load a file from a stream using the appropriate loader.
        
        Args:
            stream: File-like object with read method
            file_name: Name to assign to the file
            mime_type: Optional MIME type override
            
        Returns:
            DocHandle: Normalized file handle with content and metadata
        """
        # Use mime_type if provided, otherwise guess from file_name
        if mime_type is None:
            mime_type = mimetypes.guess_type(file_name)[0]
        
        # Determine loader based on MIME type or file extension
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        if mime_type == "application/pdf" or ext == ".pdf":
            loader_class = PDFLoader
        elif mime_type == "text/csv" or ext == ".csv":
            loader_class = CSVLoader
        elif mime_type == "application/json" or ext == ".json":
            loader_class = JSONLoader
        elif mime_type and mime_type.startswith("text/") or ext in [".txt", ".md", ".bib"]:
            loader_class = TextFileLoader
        else:
            loader_class = BinaryFileLoader
        
        # Use the loader to load from the stream
        return loader_class.load_from_stream(stream, file_name, mime_type)
    
    @classmethod
    def get_text_content(cls, doc_handle: DocHandle) -> str:
        """
        Extract text content from a DocHandle.
        For text files, returns the text.
        For binary files, raises NotImplementedError as specific extractors are needed.
        
        Args:
            doc_handle: The document handle
            
        Returns:
            str: Text content
            
        Raises:
            NotImplementedError: For binary files that need specific extractors
        """
        # If text is already available, return it
        if doc_handle.text is not None:
            return doc_handle.text
        
        # Check if it's a text-based file we can decode
        mime_type = doc_handle.mime_type or ""
        if mime_type.startswith("text/") or mime_type in ["application/json", "application/xml", "application/x-bibtex"]:
            try:
                return doc_handle.content.decode("utf-8")
            except UnicodeDecodeError:
                return doc_handle.content.decode("latin-1")
                
        raise NotImplementedError(
            f"Text extraction not implemented for mime type: {mime_type}. "
            "Use specific extractors from the chunker module."
        )
