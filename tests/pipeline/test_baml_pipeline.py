"""
Tests for the integration of BAML into the Structura pipeline.

These tests verify the full pipeline flow with the refactored BAML components:
1. Client generation and registration
2. Planner integration with BAML
3. Extractor integration with BAML
"""

import unittest
import logging
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.baml_utils import generate_client, client_registry_service
from src.pipeline.planner.planner import Planner, ExtractionPlan
from src.pipeline.extractor import Extractor
from src.pipeline.chunker.text_chunker import TextChunker, Chunk
from src.pipeline.loader.doc_handle import DocHandle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestBAMLPipeline(unittest.TestCase):
    """Test cases for the BAML integration with the pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a simple document handle
        self.doc_handle = DocHandle(
            file_path="test.txt",
            content=b"This is a test document with information about John Smith, a 45-year-old software engineer.",
            text="This is a test document with information about John Smith, a 45-year-old software engineer.",
            metadata={"source": "test"}
        )
        
        # Create a simple schema
        self.schema_json = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "occupation": {"type": "string"}
            }
        }
        
        self.schema_baml = """
        class PersonInfo {
            name string @description("The person's full name")
            age int @description("The person's age in years")
            occupation string @description("The person's job or profession")
        }
        """
        
        # Patch ensure_client to avoid actual client generation
        self.ensure_client_patcher = patch('src.pipeline.extractor.extractor.Extractor._ensure_client')
        self.mock_ensure_client = self.ensure_client_patcher.start()
        self.mock_ensure_client.return_value = True
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.ensure_client_patcher.stop()
    
    @patch('src.pipeline.extractor.extractor.importlib.import_module')
    @patch('src.baml_utils.client_registry_service.get_registry')
    @patch('src.baml_utils.client_registry_service.get_collector')
    def test_planner_extractor_integration(self, mock_get_collector, mock_get_registry, mock_import_module):
        """Test integration between planner and extractor with BAML."""
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
        mock_result.data = json.dumps({
            "name": "John Smith",
            "age": 45,
            "occupation": "software engineer"
        })
        mock_client.extractor.return_value = mock_result
        
        # Create a planner and generate a plan
        planner = Planner()
        plan = planner.plan(self.doc_handle, self.schema_json, self.schema_baml)
        
        # Verify the plan was created correctly
        self.assertEqual(plan.doc_handle, self.doc_handle)
        self.assertEqual(plan.schema_json, self.schema_json)
        self.assertEqual(plan.schema_baml, self.schema_baml)
        
        # Create a chunker and chunk the document (if needed)
        chunker = TextChunker()
        if plan.needs_chunking:
            chunks = chunker.chunk(self.doc_handle)
        else:
            # If no chunking needed, create a single chunk manually
            chunks = [Chunk(
                text=self.doc_handle.text,
                metadata=self.doc_handle.metadata,
                index=0,
                total_chunks=1
            )]
        
        # Create an extractor and extract structured data
        extractor = Extractor()
        result = extractor.extract(chunks, plan)
        
        # Verify the extraction result
        self.assertEqual(result, {
            "name": "John Smith",
            "age": 45,
            "occupation": "software engineer"
        })
        
        # Verify the client was called with the correct parameters
        mock_client.extractor.assert_called_once()
    
    @patch('src.baml_utils.client_generator.subprocess.run')
    def test_client_generator(self, mock_subprocess_run):
        """Test the BAML client generator."""
        # Mock successful generation
        mock_subprocess_run.return_value = MagicMock(
            stdout="Generated client files",
            stderr="",
            returncode=0
        )
        
        # Mock the client directory check
        with patch('src.baml_utils.client_generator.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.glob.return_value = [MagicMock()]
            mock_path_instance.__truediv__.return_value = mock_path_instance
            mock_path.return_value = mock_path_instance
            
            # Test generating the client
            success = generate_client(force=True)
            
            # Verify the result
            self.assertTrue(success)
            
            # Verify the subprocess was called with the correct parameters
            mock_subprocess_run.assert_called_once()
            
            # Make sure we specified from and output paths
            call_args = mock_subprocess_run.call_args[0][0]
            self.assertIn("--from", call_args)
            self.assertIn("--output", call_args)


if __name__ == "__main__":
    unittest.main() 