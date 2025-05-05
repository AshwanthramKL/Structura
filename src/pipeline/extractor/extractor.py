"""
Extractor component for structured data extraction.

The extractor uses BAML prompts to convert unstructured content (text or images)
into structured data according to a JSON schema.
"""

import json
import logging
import base64
from typing import Dict, Any, List, Optional, Tuple

from baml_py import ClientRegistry, Image
from baml_client import b

from src.pipeline.planner.planner import ExtractionPlan
from src.pipeline.chunker.text_chunker import Chunk
from src.schema_compiler.validator import SchemaValidator

logger = logging.getLogger(__name__)


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
            return self._extract_from_chunk(chunks[0], plan)
        
        # For multiple chunks, extract from each and combine
        results = []
        errors = []
        
        for i, chunk in enumerate(chunks):
            try:
                result = self._extract_from_chunk(chunk, plan)
                results.append(result)
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
    
    def _extract_from_chunk(self, chunk: Chunk, plan: ExtractionPlan) -> Dict[str, Any]:
        """
        Extract structured data from a single chunk using the extraction plan.
        
        Args:
            chunk: Text or image chunk to extract from
            plan: Extraction plan from the planner
            
        Returns:
            Extracted structured data conforming to the schema
        """
        # Configure BAML client for the specified model
        registry = self._configure_client(plan.model_tier)
        
        # Handle different types of chunks
        if chunk.images:
            return self._extract_from_images(chunk.images, plan, registry)
        elif chunk.text:
            return self._extract_from_text(chunk.text, plan, registry)
        else:
            raise ValueError("Chunk contains neither text nor images")
    
    def _extract_from_text(self, text: str, plan: ExtractionPlan, 
                          registry: ClientRegistry) -> Dict[str, Any]:
        """
        Extract from text content with retry capability.
        
        Args:
            text: The text content to extract from
            plan: Extraction plan containing schema information
            registry: Configured BAML client registry
            
        Returns:
            Extracted structured data
        """
        if not text.strip():
            raise ValueError("Empty text content")
        
        # Try extraction with retries
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Call BAML client with the text input
                # Access the BAML function dynamically as it's generated from the BAML files
                result_json = getattr(b, "extractor")(
                    input=text,
                    schema=plan.schema_baml,
                    is_image=False,
                    client_registry=registry
                )
                
                # Parse and validate the result
                return self._parse_and_validate(result_json, plan.schema_json)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Extraction attempt {attempt+1} failed: {last_error}")
        
        # If we get here, all attempts failed
        raise ValueError(f"All extraction attempts failed. Last error: {last_error}")
    
    def _extract_from_images(self, images: List[bytes], plan: ExtractionPlan,
                            registry: ClientRegistry) -> Dict[str, Any]:
        """
        Extract from image content.
        
        Args:
            images: List of image data
            plan: Extraction plan containing schema information
            registry: Configured BAML client registry
            
        Returns:
            Extracted structured data
        """
        if not images:
            raise ValueError("Empty image list")
        
        # Convert image bytes to BAML Image objects
        baml_images = []
        for image_data in images:
            try:
                # Convert binary image data to base64 string first
                image_b64 = base64.b64encode(image_data).decode('utf-8')
                
                # Create BAML Image from base64 string
                baml_image = Image.from_base64("image/png", image_b64)
                baml_images.append(baml_image)
            except Exception as e:
                logger.error(f"Failed to process image: {str(e)}")
                # Continue with other images if one fails
        
        if not baml_images:
            raise ValueError("Failed to process any images in the chunk")
        
        try:
            # Call BAML client with the image inputs
            # Access the BAML function dynamically as it's generated from the BAML files
            result_json = getattr(b, "extractor")(
                input=baml_images,
                schema=plan.schema_baml,
                is_image=True,
                client_registry=registry
            )
            
            # Parse and validate the result
            return self._parse_and_validate(result_json, plan.schema_json)
        except Exception as e:
            error_msg = f"Image extraction failed: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _configure_client(self, model_tier: str) -> ClientRegistry:
        """
        Configure BAML client for the specified model tier.
        
        Args:
            model_tier: The model tier to use (mini, flash, full, pro)
            
        Returns:
            Configured BAML client registry
        """
        registry = ClientRegistry()
        
        # Configure based on model tier
        if model_tier == "mini":
            registry.add_llm_client(
                name="StructuraMini",
                provider="openai",
                options={
                    "model": "gpt-4-0125-preview",
                    "temperature": 0.2,
                    "max_tokens": 4096
                }
            )
            registry.set_primary("StructuraMini")
        elif model_tier == "flash":
            registry.add_llm_client(
                name="StructuraFlash",
                provider="google-ai",
                options={
                    "model": "gemini-1.5-flash",
                    "temperature": 0.2,
                    "max_tokens": 8192
                }
            )
            registry.set_primary("StructuraFlash")
        elif model_tier == "full":
            registry.add_llm_client(
                name="StructuraFull",
                provider="openai",
                options={
                    "model": "gpt-4-turbo",
                    "temperature": 0.2,
                    "max_tokens": 4096
                }
            )
            registry.set_primary("StructuraFull")
        elif model_tier == "pro":
            registry.add_llm_client(
                name="StructuraPro",
                provider="google-ai",
                options={
                    "model": "gemini-1.5-pro",
                    "temperature": 0.2,
                    "max_tokens": 8192
                }
            )
            registry.set_primary("StructuraPro")
        else:
            # Default to mini if unknown tier
            logger.warning(f"Unknown model tier: {model_tier}, defaulting to mini")
            registry.add_llm_client(
                name="StructuraDefault",
                provider="openai",
                options={
                    "model": "gpt-4-0125-preview",
                    "temperature": 0.2,
                    "max_tokens": 4096
                }
            )
            registry.set_primary("StructuraDefault")
        
        return registry
    
    def _parse_and_validate(self, json_str: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON string and validate against schema.
        
        Args:
            json_str: JSON string to parse
            schema: JSON schema to validate against
            
        Returns:
            Parsed and validated data
            
        Raises:
            ValueError: If parsing or validation fails
        """
        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        
        # Validate against schema
        try:
            is_valid, errors = SchemaValidator.validate(
                data, schema, raise_exception=False
            )
            
            if not is_valid:
                error_paths = [e["path"] for e in errors]
                logger.warning(f"Schema validation failed at: {', '.join(error_paths)}")
                # We still return the data even if validation fails
            
            return data
        except Exception as e:
            logger.error(f"Schema validation error: {str(e)}")
            raise ValueError(f"Schema validation error: {str(e)}")
