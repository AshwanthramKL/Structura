import os
import io
from typing import Dict, Any, Optional, BinaryIO, TextIO, Union

from src.pipeline.loader.base_loader import BaseFileLoader
from src.pipeline.loader.doc_handle import DocHandle

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

class PDFLoader(BaseFileLoader):
    """Loader specific to PDF files"""
    
    @classmethod
    def _get_pdf_page_count(cls, content: bytes) -> int:
        """Get the page count of a PDF document."""
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
        """Load a PDF file from disk into a DocHandle."""
        # Ensure MIME types are registered
        cls.initialize()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file content
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Get basic metadata
        metadata = cls.get_basic_metadata(file_path)
        
        # Add PDF-specific metadata
        page_count = cls._get_pdf_page_count(content)
        if page_count > 0:
            metadata["page_count"] = str(page_count)
        
        # Create DocHandle - text extraction will be handled by chunker
        return DocHandle(
            file_path=file_path,
            content=content,
            text=None,  # PDF text extraction deferred to chunker
            metadata=metadata
        )
    
    @classmethod
    def load_from_stream(
        cls,
        stream: Union[BinaryIO, TextIO],
        file_name: str,
        mime_type: Optional[str] = None
    ) -> DocHandle:
        """Load a PDF file from a stream into a DocHandle."""
        # Ensure MIME types are registered
        cls.initialize()
        
        # Read content (PDFs should always be binary)
        content = stream.read()
        if not isinstance(content, bytes):
            if isinstance(content, str):
                content = content.encode('utf-8')
            else:
                content = bytes(str(content), 'utf-8')
        
        # Get basic metadata
        metadata = cls.get_basic_metadata(file_name)
        
        # Add PDF-specific metadata
        page_count = cls._get_pdf_page_count(content)
        if page_count > 0:
            metadata["page_count"] = str(page_count)
        
        return DocHandle(
            file_path=file_name,
            content=content,
            mime_type=mime_type or "application/pdf",
            text=None,  # PDF text extraction deferred to chunker
            metadata=metadata
        ) 