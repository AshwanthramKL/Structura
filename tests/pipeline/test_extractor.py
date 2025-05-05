"""
Tests for the Extractor component.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, ANY

from src.pipeline.extractor.extractor import Extractor
from src.pipeline.planner.planner import ExtractionPlan
from src.pipeline.chunker.text_chunker import Chunk
from src.pipeline.loader.doc_handle import DocHandle


class TestExtractor:
    """Test suite for the Extractor component."""
    
    @pytest.fixture
    def mock_baml_module(self):
        """Mock for the BAML module"""
        with patch("src.pipeline.extractor.extractor.b") as mock_b:
            # Setup mock extractor function
            mock_extractor = MagicMock()
            mock_extractor.return_value = json.dumps({"name": "Test", "age": 30})
            # Set the extractor attribute dynamically
            setattr(mock_b, "extractor", mock_extractor)
            yield mock_b
    
    @pytest.fixture
    def sample_schema(self):
        """Sample JSON schema for testing."""
        return {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
    
    @pytest.fixture
    def sample_schema_baml(self):
        """Sample BAML schema for testing."""
        return """
        type Person {
            name: string
            age: int
        }
        """
    
    @pytest.fixture
    def sample_doc_handle(self):
        """Sample document handle for testing."""
        return DocHandle(
            file_path="test.txt",
            content=b"Test content",
            text="This is John Doe, aged 30 years old."
        )
    
    @pytest.fixture
    def sample_extraction_plan(self, sample_schema, sample_schema_baml, sample_doc_handle):
        """Sample extraction plan for testing."""
        return ExtractionPlan(
            doc_handle=sample_doc_handle,
            schema_json=sample_schema,
            schema_baml=sample_schema_baml,
            needs_chunking=False,
            model_tier="mini",
            total_input_tokens=100,
            expected_output_tokens=50,
            arrays=[],
            arrays_for_streaming=[]
        )
    
    @pytest.fixture
    def sample_text_chunk(self):
        """Sample text chunk for testing."""
        return Chunk(
            text="This is John Doe, aged 30 years old.",
            metadata={
                "file_path": "test.txt",
                "mime_type": "text/plain"
            }
        )
    
    @pytest.fixture
    def sample_image_chunk(self):
        """Sample image chunk for testing."""
        return Chunk(
            images=[b"test_image_data"],
            metadata={
                "file_path": "test.pdf",
                "mime_type": "application/pdf"
            }
        )
    
    @patch("src.pipeline.extractor.extractor.ClientRegistry")
    def test_extract_from_text_chunk(self, mock_registry_class, mock_baml_module, 
                                     sample_text_chunk, sample_extraction_plan):
        """Test extraction from a text chunk."""
        # Configure mocks
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        
        # Create extractor and extract
        extractor = Extractor()
        result = extractor._extract_from_chunk(sample_text_chunk, sample_extraction_plan)
        
        # Assertions
        assert result == {"name": "Test", "age": 30}
        mock_baml_module.extractor.assert_called_once_with(
            input=sample_text_chunk.text,
            schema=sample_extraction_plan.schema_baml,
            is_image=False,
            client_registry=mock_registry
        )
        
    @patch("src.pipeline.extractor.extractor.ClientRegistry")
    @patch("src.pipeline.extractor.extractor.Image")
    def test_extract_from_image_chunk(self, mock_image_class, mock_registry_class, 
                                      mock_baml_module, sample_image_chunk, 
                                      sample_extraction_plan):
        """Test extraction from an image chunk."""
        # Configure mocks
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        mock_image = MagicMock()
        mock_image_class.from_base64.return_value = mock_image
        
        # Create extractor and extract
        extractor = Extractor()
        result = extractor._extract_from_chunk(sample_image_chunk, sample_extraction_plan)
        
        # Assertions
        assert result == {"name": "Test", "age": 30}
        mock_image_class.from_base64.assert_called_once()
        mock_baml_module.extractor.assert_called_once_with(
            input=ANY,  # Could be a list of image objects
            schema=sample_extraction_plan.schema_baml,
            is_image=True,
            client_registry=mock_registry
        )
    
    @patch("src.pipeline.extractor.extractor.ClientRegistry")
    def test_extract_with_empty_chunk(self, mock_registry_class, mock_baml_module, 
                                     sample_extraction_plan):
        """Test extraction fails with empty chunk."""
        # Configure mocks
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        
        # Create an empty chunk with neither text nor images
        empty_chunk = Chunk(text="")
        
        # Create extractor and extract
        extractor = Extractor()
        with pytest.raises(ValueError, match="Chunk contains neither text nor images"):
            extractor._extract_from_chunk(empty_chunk, sample_extraction_plan)
    
    @patch("src.pipeline.extractor.extractor.ClientRegistry")
    def test_extract_handles_multiple_chunks(self, mock_registry_class, mock_baml_module,
                                           sample_text_chunk, sample_extraction_plan):
        """Test that the extract method can handle multiple chunks."""
        # Configure mocks
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        
        # Create multiple chunks
        chunk1 = sample_text_chunk
        chunk2 = Chunk(text="This is Jane Smith, aged 25.")
        
        # Create extractor and extract
        extractor = Extractor()
        result = extractor.extract([chunk1, chunk2], sample_extraction_plan)
        
        # Should return the first successful result
        assert result == {"name": "Test", "age": 30}
        # Should call the extractor twice (once for each chunk)
        assert mock_baml_module.extractor.call_count == 2
    
    @patch("src.pipeline.extractor.extractor.ClientRegistry")
    def test_configure_client(self, mock_registry_class):
        """Test client configuration for different model tiers."""
        # Configure mocks
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        
        # Test different tiers
        extractor = Extractor()
        
        # Test mini tier
        extractor._configure_client("mini")
        mock_registry.add_llm_client.assert_called_with(
            name="StructuraMini",
            provider="openai",
            options={
                "model": "gpt-4-0125-preview",
                "temperature": 0.2,
                "max_tokens": 4096
            }
        )
        mock_registry.set_primary.assert_called_with("StructuraMini")
        
        # Reset mock
        mock_registry.reset_mock()
        
        # Test flash tier
        extractor._configure_client("flash")
        mock_registry.add_llm_client.assert_called_with(
            name="StructuraFlash",
            provider="google-ai", 
            options={
                "model": "gemini-1.5-flash",
                "temperature": 0.2,
                "max_tokens": 8192
            }
        )
        mock_registry.set_primary.assert_called_with("StructuraFlash")
    
    @patch("src.pipeline.extractor.extractor.ClientRegistry")
    def test_handle_invalid_model_tier(self, mock_registry_class):
        """Test handling of invalid model tier."""
        # Configure mocks
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        
        # Test unknown tier
        extractor = Extractor()
        extractor._configure_client("invalid_tier")
        
        # Should default to mini tier
        mock_registry.add_llm_client.assert_called_with(
            name="StructuraDefault",
            provider="openai",
            options={
                "model": "gpt-4-0125-preview",
                "temperature": 0.2,
                "max_tokens": 4096
            }
        )
        mock_registry.set_primary.assert_called_with("StructuraDefault") 