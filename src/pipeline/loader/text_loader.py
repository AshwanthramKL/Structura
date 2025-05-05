import os
from typing import Dict, Any, Optional, BinaryIO, TextIO, Union, cast

from src.pipeline.loader.base_loader import BaseFileLoader
from src.pipeline.loader.doc_handle import DocHandle

class TextFileLoader(BaseFileLoader):
    """Base loader for text-based files"""
    
    @classmethod
    def load_file(cls, file_path: str) -> DocHandle:
        """Load a text file from disk into a DocHandle."""
        # Ensure MIME types are registered
        cls.initialize()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file content
        with open(file_path, "rb") as f:
            binary_content = f.read()
        
        # Try to decode text
        try:
            text_content = binary_content.decode("utf-8")
        except UnicodeDecodeError:
            # Fall back to latin-1 if UTF-8 fails
            text_content = binary_content.decode("latin-1")
        
        # Get basic metadata
        metadata = cls.get_basic_metadata(file_path)
        
        # Create DocHandle
        return DocHandle(
            file_path=file_path,
            content=binary_content,
            text=text_content,
            metadata=metadata
        )
    
    @classmethod
    def load_from_stream(
        cls,
        stream: Union[BinaryIO, TextIO],
        file_name: str,
        mime_type: Optional[str] = None
    ) -> DocHandle:
        """Load a text file from a stream into a DocHandle."""
        # Ensure MIME types are registered
        cls.initialize()
        
        # Determine if we have binary or text stream
        is_binary = hasattr(stream, 'mode') and 'b' in getattr(stream, 'mode', '')
        
        # Read content
        if is_binary:
            # Handle binary stream
            binary_content = cast(BinaryIO, stream).read()
            if isinstance(binary_content, bytes):
                try:
                    text_content = binary_content.decode("utf-8")
                except UnicodeDecodeError:
                    text_content = binary_content.decode("latin-1")
            else:
                # In case we got something unexpected
                text_content = str(binary_content)
                binary_content = text_content.encode('utf-8')
        else:
            # Handle text stream
            text_content = cast(TextIO, stream).read()
            if isinstance(text_content, str):
                binary_content = text_content.encode('utf-8')
            else:
                # In case we got something unexpected
                binary_content = cast(bytes, text_content)
                text_content = str(binary_content)
        
        # Get basic metadata
        metadata = cls.get_basic_metadata(file_name)
        
        return DocHandle(
            file_path=file_name,
            content=binary_content,
            mime_type=mime_type,
            text=text_content,
            metadata=metadata
        )


class CSVLoader(TextFileLoader):
    """Specialized loader for CSV files"""
    # Can implement CSV-specific functionality here
    # For now, inherits all behavior from TextFileLoader
    pass


class JSONLoader(TextFileLoader):
    """Specialized loader for JSON files"""
    # Can implement JSON-specific functionality here
    # For now, inherits all behavior from TextFileLoader
    pass 