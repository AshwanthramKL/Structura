import mimetypes
from typing import Dict, Any, Optional

class DocHandle:
    """
    Normalizes file input into a consistent handle with metadata.
    
    Attributes:
        file_path (str): Original file path
        mime_type (str): MIME type of the file
        content (bytes): Raw file content
        text (Optional[str]): Text content if available
        size (int): File size in bytes
        metadata (Dict[str, str]): Additional file metadata
    """
    def __init__(
        self, 
        file_path: str, 
        content: bytes,
        mime_type: Optional[str] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ):
        self.file_path = file_path
        self.content = content
        self.size = len(content)
        self.mime_type = mime_type or mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        self.text = text
        self.metadata = metadata or {}
        
    def __repr__(self) -> str:
        return f"DocHandle(path='{self.file_path}', mime={self.mime_type}, size={self.size})" 