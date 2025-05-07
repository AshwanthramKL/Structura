"""
Tests for the refactored Extractor component.

These tests verify that the extractor properly:
1. Integrates with the BAML client
2. Handles text and image extraction
3. Returns appropriate results
"""

import unittest
import json
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from src.pipeline.extractor import Extractor, ExtractionResult
from src.pipeline.planner.planner import ExtractionPlan
from src.pipeline.chunker.text_chunker import Chunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestExtractor(unittest.TestCase):
    """Test cases for the refactored Extractor component."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock extraction plan
        self.mock_plan = MagicMock(spec=ExtractionPlan)
        self.mock_plan.model_tier = "mini"
        self.mock_plan.schema_baml = "class TestSchema { data string }"
        self.mock_plan.schema_json = {"type": "object", "properties": {"data": {"type": "string"}}}
        
        # Create a text chunk
        self.text_chunk = Chunk(
            text="This is a test document containing important information.",
            metadata={"source": "test"},
            index=0,
            total_chunks=1
        )
        
        # Patch the _ensure_client method to avoid actual client generation
        self.ensure_client_patcher = patch('src.pipeline.extractor.extractor.Extractor._ensure_client')
        self.mock_ensure_client = self.ensure_client_patcher.start()
        self.mock_ensure_client.return_value = True
        
        # Create the extractor instance
        self.extractor = Extractor()
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.ensure_client_patcher.stop()
    
    @patch('src.pipeline.extractor.extractor.importlib.import_module')
    @patch('src.baml_utils.client_registry_service.get_registry')
    @patch('src.baml_utils.client_registry_service.get_collector')
    def test_extract_from_text_success(self, mock_get_collector, mock_get_registry, mock_import_module):
        """Test successful text extraction."""
        # Mock the registry and collector
        mock_registry = MagicMock()
        mock_collector = MagicMock()
        mock_get_registry.return_value = mock_registry
        mock_get_collector.return_value = mock_collector
        
        # Mock the BAML client module
        mock_baml_client = MagicMock()
        mock_client = MagicMock()
        mock_baml_client.b.with_options.return_value = mock_client
        mock_import_module.return_value = mock_baml_client
        
        # Mock the extractor function result
        mock_result = MagicMock()
        mock_result.data = json.dumps({"data": "Extracted information"})
        mock_client.Extractor.return_value = mock_result
        
        # Mock the collector logs
        mock_collector.logs = [MagicMock()]
        mock_collector.logs[0].usage.total_tokens = 100
        mock_collector.logs[0].usage.input_tokens = 75
        mock_collector.logs[0].usage.output_tokens = 25
        
        # Perform extraction
        result = self.extractor.extract([self.text_chunk], self.mock_plan)
        
        # Verify the result
        self.assertEqual(result, {"data": "Extracted information"})
        
        # Verify the client was called correctly
        mock_client.Extractor.assert_called_once_with(
            input=self.text_chunk.text,
            schema=self.mock_plan.schema_baml,
            is_image=False
        )
    
    @patch('src.pipeline.extractor.extractor.importlib.import_module')
    @patch('src.baml_utils.client_registry_service.get_registry')
    @patch('src.baml_utils.client_registry_service.get_collector')
    def test_extract_with_failure(self, mock_get_collector, mock_get_registry, mock_import_module):
        """Test extraction with failure."""
        # Mock the registry and collector
        mock_registry = MagicMock()
        mock_collector = MagicMock()
        mock_get_registry.return_value = mock_registry
        mock_get_collector.return_value = mock_collector
        
        # Mock the BAML client module
        mock_baml_client = MagicMock()
        mock_client = MagicMock()
        mock_baml_client.b.with_options.return_value = mock_client
        mock_import_module.return_value = mock_baml_client
        
        # Make the extractor function raise an exception
        mock_client.Extractor.side_effect = Exception("Extraction failed")
        
        # Perform extraction (should return empty dict on failure)
        result = self.extractor.extract([self.text_chunk], self.mock_plan)
        
        # Verify the result
        self.assertEqual(result, {})
        
        # Verify the client was called
        mock_client.Extractor.assert_called_once()
    
    @patch('src.pipeline.extractor.extractor.importlib.import_module')
    @patch('src.baml_utils.client_registry_service.get_registry')
    @patch('src.baml_utils.client_registry_service.get_collector')
    def test_multiple_chunks(self, mock_get_collector, mock_get_registry, mock_import_module):
        """Test extraction with multiple chunks."""
        # Mock the registry and collector
        mock_registry = MagicMock()
        mock_collector = MagicMock()
        mock_get_registry.return_value = mock_registry
        mock_get_collector.return_value = mock_collector
        
        # Mock the BAML client module
        mock_baml_client = MagicMock()
        mock_client = MagicMock()
        mock_baml_client.b.with_options.return_value = mock_client
        mock_import_module.return_value = mock_baml_client
        
        # Mock the extractor function results
        def side_effect(*args, **kwargs):
            mock_result = MagicMock()
            # Return different data based on which chunk is being processed
            if "chunk 1" in args[0]:
                mock_result.data = json.dumps({"data": "Chunk 1 data"})
            else:
                mock_result.data = json.dumps({"data": "Chunk 2 data"})
            return mock_result
        
        mock_client.Extractor.side_effect = side_effect
        
        # Create multiple chunks
        chunk1 = Chunk(
            text="This is chunk 1 with information.",
            metadata={"source": "test"},
            index=0,
            total_chunks=2
        )
        
        chunk2 = Chunk(
            text="This is chunk 2 with more information.",
            metadata={"source": "test"},
            index=1,
            total_chunks=2
        )
        
        # Perform extraction with multiple chunks
        result = self.extractor.extract([chunk1, chunk2], self.mock_plan)
            
        # Verify the result (first chunk's data should be returned)
        self.assertEqual(result, {"data": "Chunk 1 data"})
        
        # Verify the client was called twice (once for each chunk)
        self.assertEqual(mock_client.Extractor.call_count, 2)


if __name__ == "__main__":
    unittest.main() 