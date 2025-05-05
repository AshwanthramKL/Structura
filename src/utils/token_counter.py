"""
Token counting utilities using Gemini's API.
"""

import os
import io
from typing import Dict, Union, Optional, List, Any
from src.pipeline.loader.doc_handle import DocHandle
from src.config import settings

def count_tokens(content: Union[str, DocHandle]) -> int:
    """
    Count tokens for content using Gemini's API, which supports text and files directly.
    
    Args:
        content: Text string or DocHandle
        
    Returns:
        int: Number of tokens
    """
    try:
        from google import genai
        
        # Initialize the client with API key from settings
        if not settings.has_google_api_key:
            print("Warning: GOOGLE_API_KEY not set. Using approximation.")
            # Fallback approximation
            if isinstance(content, str):
                return len(content) // 4
            elif isinstance(content, DocHandle):
                if content.text is not None:
                    return len(content.text) // 4
                else:
                    return content.size // 4
            return 500  # Default fallback
            
        client = genai.Client(api_key=settings.google_api_key)
        
        # Handle different input types
        if isinstance(content, DocHandle):
            # For DocHandle with PDF, upload the file
            if content.mime_type == "application/pdf":
                try:
                    # Convert bytes to BytesIO object
                    file_obj = io.BytesIO(content.content)
                    file_obj.name = content.file_path  # Set a name for the file
                    
                    uploaded_file = client.files.upload(file=file_obj)
                    response = client.models.count_tokens(
                        model="gemini-2.0-flash", 
                        contents=[uploaded_file]
                    )
                    token_count = response.total_tokens
                    if token_count is not None:
                        return token_count
                    return settings.tokens_per_page_estimate  # Default if None
                except Exception as e:
                    print(f"Warning: Error uploading PDF: {e}")
                    # Fallback: estimate based on page count
                    page_count = int(content.metadata.get("page_count", "0"))
                    return page_count * settings.tokens_per_page_estimate  # Use configured value
            
            # For text content
            elif content.text is not None:
                response = client.models.count_tokens(
                    model="gemini-2.0-flash", 
                    contents=content.text
                )
                token_count = response.total_tokens
                if token_count is not None:
                    return token_count
                return 500  # Default if None
            
            # For other binary content
            else:
                try:
                    # Convert bytes to BytesIO object
                    file_obj = io.BytesIO(content.content)
                    file_obj.name = content.file_path  # Set a name for the file
                    
                    uploaded_file = client.files.upload(file=file_obj)
                    response = client.models.count_tokens(
                        model="gemini-2.0-flash", 
                        contents=[uploaded_file]
                    )
                    token_count = response.total_tokens
                    if token_count is not None:
                        return token_count
                    return 500  # Default if None
                except Exception as e:
                    print(f"Warning: Error uploading file: {e}")
                    # Fallback: estimate based on file size
                    return content.size // 4
        
        # For plain text
        else:
            response = client.models.count_tokens(
                model="gemini-2.0-flash", 
                contents=content
            )
            token_count = response.total_tokens
            if token_count is not None:
                return token_count
            return len(content) // 4  # Default if None
            
    except Exception as e:
        print(f"Warning: Error counting tokens: {e}")
        # Fallback approximation
        if isinstance(content, str):
            return len(content) // 4
        elif isinstance(content, DocHandle):
            if content.text is not None:
                return len(content.text) // 4
            else:
                return content.size // 4
        return 500  # Default fallback