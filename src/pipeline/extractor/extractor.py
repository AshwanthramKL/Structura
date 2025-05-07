"""
Extractor component for structured data extraction.

The extractor uses BAML prompts to convert unstructured content (text or images)
into structured data according to a JSON schema.
"""

import json
import logging
import base64
from typing import Dict, Any, List, Optional, Tuple, Union
import importlib
import time

from baml_py import Image as BAMLImage
from pydantic import BaseModel

from src.pipeline.planner.planner import ExtractionPlan
from src.pipeline.chunker.text_chunker import Chunk
from src.schema_compiler.validator import SchemaValidator
from src.schema_compiler.converter import baml_to_json_schema, json_schema_to_typebuilder_baml
from src.baml_utils import generate_client, client_registry_service

# Note: We dynamically import TypeBuilder and other BAML client modules using importlib.import_module().
# This approach avoids linter errors and handles the case where the BAML client hasn't been generated yet.
# The BAML client is generated at runtime by _ensure_client() before extraction.

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    """
    Result of an extraction operation.
    
    Attributes:
        data: The extracted structured data
        success: Whether the extraction was successful
        error: Error message if extraction failed
        tokens: Token usage information
    """
    data: Dict[str, Any] = {}
    success: bool = True
    error: Optional[str] = None
    tokens: Dict[str, int] = {}


class Extractor:
    """
    Extracts structured data from text or image chunks according to a schema.
    
    This component:
    1. Takes a chunk of text or images and a schema
    2. Uses a BAML prompt to guide the LLM
    3. Returns structured data conforming to the schema
    """
    
    def __init__(self, max_retries: int = 2):
        """
        Initialize the extractor.
        
        Args:
            max_retries: Maximum number of retry attempts for failed extractions
        """
        self.max_retries = max_retries
        self._ensure_client()
    
    def extract(self, chunks: List[Chunk], plan: ExtractionPlan) -> Dict[str, Any]:
        """
        Extract structured data from chunks.
        
        This is the main entry point for extraction. It processes each chunk
        and combines the results.
        
        Args:
            chunks: List of chunks to extract from
            plan: Extraction plan from the planner
            
        Returns:
            Dict containing structured data conforming to the schema
        """
        # For a single chunk, just extract directly
        if len(chunks) == 1:
            result = self._extract_from_chunk(chunks[0], plan)
            if result.success:
                return result.data
            else:
                logger.error(f"Extraction failed: {result.error}")
                return {}
        
        # For multiple chunks, extract from each and combine
        results = []
        errors = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Extracting from chunk {i+1}/{len(chunks)}")
            try:
                result = self._extract_from_chunk(chunk, plan)
                if result.success:
                    results.append(result.data)
                else:
                    errors.append(f"Chunk {i+1}: {result.error}")
            except Exception as e:
                error_msg = f"Extraction from chunk {i+1}/{len(chunks)} failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # If all chunks failed, return an empty object
        if not results:
            logger.error(f"All chunks failed extraction. Errors: {errors}")
            return {}
        
        # TODO: Implement proper merging with dedicated Merger component
        # For now, we'll just return the first successful result
        return results[0]
    
    def _extract_from_chunk(self, chunk: Chunk, plan: ExtractionPlan) -> ExtractionResult:
        """
        Extract structured data from a single chunk using the extraction plan.
        
        Args:
            chunk: Text or image chunk to extract from
            plan: Extraction plan from the planner
            
        Returns:
            ExtractionResult containing the extraction result
        """
        # Ensure we have a valid BAML client
        if not self._ensure_client():
            return ExtractionResult(
                success=False,
                error="Failed to generate BAML client",
                data={}
            )
        
        # Configure BAML client for the specified model
        registry = client_registry_service.get_registry(plan.model_tier)
        collector = client_registry_service.get_collector()
        
        # Create client with options
        try:
            # Import the client module dynamically to avoid linter errors
            # This will be available after _ensure_client() is called
            baml_client = importlib.import_module("src.baml_client")
            
            # Create client with registry and collector
            client = baml_client.b.with_options(
                client_registry=registry,
                collector=collector
            )
        except ImportError as e:
            logger.error(f"Failed to import BAML client: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"BAML client import error: {str(e)}",
                data={}
            )
        except Exception as e:
            logger.error(f"Failed to create BAML client: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"BAML client error: {str(e)}",
                data={}
            )
        
        # Handle different types of chunks
        try:
            if chunk.images:
                    return self._extract_from_images(client, chunk.images, plan)
            elif chunk.text:
                    return self._extract_from_text(client, chunk.text, plan)
            else:
                    return ExtractionResult(
                        success=False,
                        error="Chunk contains neither text nor images",
                        data={}
                    )
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"Extraction error: {str(e)}",
                data={}
            )
    
    def _extract_from_text(self, client: Any, text: str, plan: ExtractionPlan) -> ExtractionResult:
        """
        Extract from text content with TypeBuilder integration.
        
        Args:
            client: Configured BAML client
            text: The text content to extract from
            plan: Extraction plan containing schema information
            
        Returns:
            ExtractionResult with extraction result
        """
        # If the text is empty, return an empty result
        if not text.strip():
            return ExtractionResult(
                success=False,
                error="Empty text content",
                data={}
            )
        
        # Try extraction with retries
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Import and configure TypeBuilder dynamically using importlib
                # This avoids linter errors and is consistent with our client import pattern
                options = {}
                try:
                    # The TypeBuilder module will be available after _ensure_client() is called
                    type_builder_module = importlib.import_module("src.baml_client.type_builder")
                    tb = type_builder_module.TypeBuilder()
                    
                    # Generate BAML schema for TypeBuilder
                    baml_schema = json_schema_to_typebuilder_baml(plan.schema_json)
                    
                    # Add the schema to TypeBuilder
                    tb.add_baml(baml_schema)
                    
                    # Set baml_options for the client call
                    options = {"tb": tb}
                except (ImportError, AttributeError) as e:
                    logger.warning(f"TypeBuilder not available, falling back to standard extraction: {str(e)}")
                    
                # Call BAML client with the text input and TypeBuilder if available
                result = client.Extractor(
                    input=text,
                    schema=plan.schema_baml,
                    is_image=False,
                    baml_options=options
                )
                
                # Parse result based on whether TypeBuilder was used
                if hasattr(result, 'rootObj'):
                    # TypeBuilder approach - access rootObj
                    data = self._convert_to_dict(result.rootObj)
                else:
                    # Standard approach - parse result normally
                    data = baml_to_json_schema(self._parse_result(result), plan.schema_json)
                
                # Get token usage from collector
                tokens = self._get_token_usage()
                
                # Return successful result with data and token usage
                return ExtractionResult(
                    success=True,
                    data=data,
                    tokens=tokens
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Extraction attempt {attempt+1} failed: {last_error}")
                time.sleep(1)  # Brief pause before retry
        
        # If we get here, all attempts failed
        return ExtractionResult(
            success=False,
            error=f"All extraction attempts failed. Last error: {last_error}",
            data={}
        )
    
    def _extract_from_images(self, client: Any, images: List[Tuple[bytes, str]], plan: ExtractionPlan) -> ExtractionResult:
        """
        Extract from image content with TypeBuilder integration.
        
        Args:
            client: Configured BAML client
            images: List of tuples containing (image_data, mime_type)
            plan: Extraction plan containing schema information
            
        Returns:
            ExtractionResult with extraction result
        """
        if not images:
            return ExtractionResult(
                success=False,
                error="Empty image list",
                data={}
            )
        
        # Convert image bytes to BAML Image objects
        baml_images = []
        for image_tuple in images:
            try:
                # Unpack the tuple
                image_data, mime_type = image_tuple
                
                # Convert binary image data to base64 string first
                image_b64 = base64.b64encode(image_data).decode('utf-8')
                
                # Create BAML Image using the correct MIME type
                baml_image = BAMLImage.from_base64(mime_type, image_b64)
                baml_images.append(baml_image)
            except Exception as e:
                logger.error(f"Failed to process image: {str(e)}")
                # Continue with other images if one fails
        
        if not baml_images:
            return ExtractionResult(
                success=False,
                error="Failed to process any images in the chunk",
                data={}
            )
        
        try:
            # Import and configure TypeBuilder dynamically using importlib
            # This avoids linter errors and is consistent with our client import pattern
            options = {}
            try:
                # The TypeBuilder module will be available after _ensure_client() is called
                type_builder_module = importlib.import_module("src.baml_client.type_builder")
                tb = type_builder_module.TypeBuilder()
                
                # Generate BAML schema for TypeBuilder
                baml_schema = json_schema_to_typebuilder_baml(plan.schema_json)
                
                # Add the schema to TypeBuilder
                tb.add_baml(baml_schema)
                
                # Set baml_options for the client call
                options = {"tb": tb}
            except (ImportError, AttributeError) as e:
                logger.warning(f"TypeBuilder not available, falling back to standard extraction: {str(e)}")
                
            # Call BAML client with the image inputs and TypeBuilder if available
            result = client.Extractor(
                input=baml_images,
                schema=plan.schema_baml,
                is_image=True,
                baml_options=options
            )
            
            # Parse result based on whether TypeBuilder was used
            if hasattr(result, 'rootObj'):
                # TypeBuilder approach - access rootObj
                data = self._convert_to_dict(result.rootObj)
            else:
                # Standard approach - parse result normally
                data = baml_to_json_schema(self._parse_result(result), plan.schema_json)
            
            # TODO: Use SchemaValidator to validate the data against the schema
            # validator = SchemaValidator(plan.schema_json)
            # validator.validate(data)
            
            # Get token usage from collector
            tokens = self._get_token_usage()
            
            # Return successful result with data and token usage
            return ExtractionResult(
                success=True,
                data=data,
                tokens=tokens
            )
        except Exception as e:
            error_msg = f"Image extraction failed: {str(e)}"
            logger.error(error_msg)
            return ExtractionResult(
                success=False,
                error=error_msg,
                data={}
            )
    
    def _parse_result(self, result: Any) -> Dict[str, Any]:
        """
        Parse the result from BAML client.
        
        The BAML client returns a structured object that needs to be converted to a dict.
        
        Args:
            result: Result from BAML client
            
        Returns:
            Dict representation of the result
        """
        # For StructuredData class, get the data attribute
        if hasattr(result, 'data'):
            # If data is a string (likely JSON), parse it
            if isinstance(result.data, str):
                try:
                    return json.loads(result.data)
                except json.JSONDecodeError:
                    # If not valid JSON, return as is
                    return {"data": result.data}
            else:
                # If data is not a string, it might be an object or dict already
                return {"data": result.data}
        
        # If the result is already a dict-like object, convert to dict
        if hasattr(result, '__dict__'):
            return vars(result)
        
        # If we can't parse it, return as is
        return {"result": str(result)}
    
    def _get_token_usage(self) -> Dict[str, int]:
        """
        Get token usage information from the collector.
            
        Returns:
            Dict with token usage information
        """
        collector = client_registry_service.get_collector()
        tokens = {"total": 0, "prompt": 0, "completion": 0}
        
        if collector and collector.logs:
            last_log = collector.logs[-1]
            if hasattr(last_log, 'usage') and last_log.usage:
                # Defensively get attributes in case the API changes
                usage = last_log.usage
                tokens["prompt"] = getattr(usage, "input_tokens", 0)
                tokens["completion"] = getattr(usage, "output_tokens", 0)
                tokens["total"] = getattr(usage, "total_tokens", int(tokens["prompt"]) + int(tokens["completion"]))
        
        return tokens
    
    def _ensure_client(self) -> bool:
        """
        Ensure that the BAML client is generated and available.
        
        Returns:
            bool: True if client is available, False otherwise
        """
        try:
            # PROTOTYPE APPROACH: Always regenerate client for maximum reliability
            # TODO: Optimization - Replace with timestamp-based regeneration:
            #   if not generate_client(force=False):
            #       logger.error("Failed to generate BAML client")
            #       return False
            
            # Always force regeneration to ensure client is fresh
            if not generate_client(force=True):
                logger.error("Failed to generate BAML client")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error ensuring BAML client availability: {str(e)}")
            return False

    def _convert_to_dict(self, obj: Any) -> Any:
        """
        Convert TypeBuilder-generated object to dictionary.
        
        This method handles dynamic properties that may not be visible in vars().
        
        Args:
            obj: TypeBuilder-generated object or any other object
            
        Returns:
            Dictionary representation of the object, or the value itself for primitives
        """
        if obj is None:
            return None
        
        # For primitive types, return as is
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # For list types, convert each item
        if isinstance(obj, list):
            return [self._convert_to_dict(item) for item in obj]
            
        # For dict types, convert each value
        if isinstance(obj, dict):
            return {k: self._convert_to_dict(v) for k, v in obj.items()}
        
        # First try the simplest approach - check if it's already dict-like
        try:
            result = dict(obj)
            return {k: self._convert_to_dict(v) for k, v in result.items()}
        except (TypeError, ValueError):
            # Not directly convertible to dict, continue with attribute approach
            pass
            
        # For objects with __dict__, use attribute-based approach
        result = {}
        
        try:
            # Get all non-hidden, non-callable attributes
            attrs = [attr for attr in dir(obj) 
                    if not attr.startswith("_") and not callable(getattr(obj, attr))]
            
            # If no attributes found, try using __dict__
            if not attrs and hasattr(obj, "__dict__"):
                return {k: self._convert_to_dict(v) for k, v in vars(obj).items()}
            
            for attr in attrs:
                try:
                    value = getattr(obj, attr)
                    result[attr] = self._convert_to_dict(value)
                except Exception as e:
                    logger.warning(f"Failed to get attribute {attr}: {str(e)}")
                    
            # If result is empty but object has string representation, use it
            if not result:
                return str(obj)
                
            return result
        except Exception as e:
            logger.warning(f"Failed to convert object to dict: {str(e)}")
            # Fallback to vars() if dir() approach fails
            if hasattr(obj, "__dict__"):
                return {k: self._convert_to_dict(v) for k, v in vars(obj).items()}
            # Last resort - convert to string
            return str(obj)
