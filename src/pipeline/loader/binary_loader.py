import os
from typing import Dict, Any, Optional, BinaryIO, TextIO, Union

from src.pipeline.loader.base_loader import BaseFileLoader
from src.pipeline.loader.doc_handle import DocHandle

class BinaryFileLoader(BaseFileLoader):
    """Loader for generic binary files"""
    
    @classmethod
    def load_file(cls, file_path: str) -> DocHandle:
        """Load a binary file from disk into a DocHandle."""
        # Ensure MIME types are registered
        cls.initialize()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file content
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Get basic metadata
        metadata = cls.get_basic_metadata(file_path)
        
        # Create DocHandle
        return DocHandle(
            file_path=file_path,
            content=content,
            text=None,  # No text for binary files
            metadata=metadata
        )
    
    @classmethod
    def load_from_stream(
        cls,
        stream: Union[BinaryIO, TextIO],
        file_name: str,
        mime_type: Optional[str] = None
    ) -> DocHandle:
        """Load a binary file from a stream into a DocHandle."""
        # Ensure MIME types are registered
        cls.initialize()
        
        # Read content
        content = stream.read()
        if not isinstance(content, bytes):
            if isinstance(content, str):
                content = content.encode('utf-8')
            else:
                content = bytes(str(content), 'utf-8')
        
        # Get basic metadata
        metadata = cls.get_basic_metadata(file_name)
        
        return DocHandle(
            file_path=file_name,
            content=content,
            mime_type=mime_type,
            text=None,  # No text for binary files
            metadata=metadata
        ) 