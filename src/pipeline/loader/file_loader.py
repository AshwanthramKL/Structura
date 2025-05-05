import os
import mimetypes
from typing import Dict, Any, Optional, BinaryIO, TextIO, Union, Tuple
import io

# Try to import PDF libraries, with graceful fallback
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class DocHandle:
    """
    Normalizes file input into a consistent handle with metadata.
    
    Attributes:
        file_path (str): Original file path
        mime_type (str): MIME type of the file
        content (bytes): Raw file content
        text (Optional[str]): Text content if available
        size (int): File size in bytes
        metadata (Dict[str, Any]): Additional file metadata
    """
    def __init__(
        self, 
        file_path: str, 
        content: bytes,
        mime_type: Optional[str] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.file_path = file_path
        self.content = content
        self.size = len(content)
        self.mime_type = mime_type or mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        self.text = text
        self.metadata = metadata or {}
        
    def __repr__(self) -> str:
        return f"DocHandle(path='{self.file_path}', mime={self.mime_type}, size={self.size})"


class FileLoader:
    """
    Loads files from various sources and formats into a normalized DocHandle.
    Currently supports:
    - PDF files (metadata only, content processed by chunker)
    - Images (raw bytes, processed by vision models)
    - Text files (txt, md, bib)
    - CSV files
    """
    
    @classmethod
    def initialize(cls):
        """
        Initialize the FileLoader by registering custom MIME types.
        Call this before using the FileLoader class.
        """
        # Register additional MIME types
        mimetypes.add_type('application/x-bibtex', '.bib')
        mimetypes.add_type('text/markdown', '.md')
        mimetypes.add_type('text/csv', '.csv')
    
    @staticmethod
    def _get_pdf_page_count(content: bytes) -> int:
        """
        Get the page count of a PDF document.
        
        Args:
            content: PDF file content in bytes
            
        Returns:
            int: Number of pages in the PDF, or 0 if libraries not available
        """
        if PYMUPDF_AVAILABLE:
            try:
                with fitz.open(stream=content, filetype="pdf") as pdf:
                    return len(pdf)
            except Exception:
                pass
        
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    return len(pdf.pages)
            except Exception:
                pass
                
        return 0
    
    @classmethod
    def load_file(cls, file_path: str) -> DocHandle:
        """
        Load a file from disk into a DocHandle.
        
        Args:
            file_path: Path to the file on disk
            
        Returns:
            DocHandle: Normalized file handle with content and metadata
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        # Ensure MIME types are registered
        cls.initialize()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file extension and mime type
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Read file content
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Initialize metadata
        metadata = {
            "extension": ext,
            "filename": os.path.basename(file_path)
        }
        
        # Handle text extraction for different file types
        text = None
        if ext in [".txt", ".md", ".bib", ".csv", ".json"]:
            # Text-based files
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                # Fall back to latin-1 if UTF-8 fails
                text = content.decode("latin-1") 
        elif ext == ".pdf":
            # Add PDF metadata but don't extract text
            # (Text extraction will be handled by the chunker module using vision models)
            page_count = cls._get_pdf_page_count(content)
            if page_count > 0:
                metadata["page_count"] = page_count
                
        # Create DocHandle
        return DocHandle(
            file_path=file_path,
            content=content,
            text=text,
            metadata=metadata
        )
    
    @classmethod
    def load_from_stream(
        cls,
        stream: Union[BinaryIO, TextIO],
        file_name: str,
        mime_type: Optional[str] = None
    ) -> DocHandle:
        """
        Load a file from a stream into a DocHandle.
        
        Args:
            stream: File-like object with read method
            file_name: Name to assign to the file
            mime_type: Optional MIME type override
            
        Returns:
            DocHandle: Normalized file handle with content and metadata
        """
        # Ensure MIME types are registered
        cls.initialize()
        
        # Determine if we have binary or text stream
        is_binary = hasattr(stream, 'mode') and 'b' in stream.mode
        
        # Read content
        if is_binary:
            content = stream.read()
            text = None
        else:
            text_content = stream.read()
            # Convert to bytes for storage
            content = text_content.encode('utf-8')
            text = text_content
            
        # Get extension and mime type
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        metadata = {
            "extension": ext,
            "filename": os.path.basename(file_name)
        }
        
        # For PDFs, add page count if possible
        if ext == ".pdf" or mime_type == "application/pdf":
            page_count = cls._get_pdf_page_count(content)
            if page_count > 0:
                metadata["page_count"] = page_count
        
        return DocHandle(
            file_path=file_name,
            content=content,
            mime_type=mime_type,
            text=text,
            metadata=metadata
        )
    
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
        # Ensure MIME types are registered
        cls.initialize()
        
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
