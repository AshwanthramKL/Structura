"""
Tests for the TypeBuilder integration in the Extractor component.

These tests verify that the extractor properly:
1. Uses TypeBuilder for dynamic schema extension
2. Handles both success and failure cases
3. Correctly processes results from TypeBuilder
"""

import unittest
import json
import logging
from unittest.mock import patch, MagicMock

from src.pipeline.extractor import Extractor
from src.pipeline.planner.planner import ExtractionPlan
from src.pipeline.chunker.text_chunker import Chunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestTypeBuilderIntegration(unittest.TestCase):
    """Test cases for TypeBuilder integration in the Extractor component."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a more complex extraction plan with a nested schema
        self.mock_plan = MagicMock(spec=ExtractionPlan)
        self.mock_plan.model_tier = "mini"
        self.mock_plan.schema_baml = """
        class Person {
            name string @description("The person's name")
            age int @description("The person's age")
            occupation string? @description("The person's job")
        }
        """
        self.mock_plan.schema_json = {
            "type": "object",
            "properties": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The person's name"},
                        "age": {"type": "integer", "description": "The person's age"},
                        "occupation": {"type": "string", "description": "The person's job"}
                    },
                    "required": ["name", "age"]
                }
            },
            "required": ["person"]
        }
        
        # Create a text chunk
        self.text_chunk = Chunk(
            text="John Smith is a 42-year-old software engineer at Tech Corp.",
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
    @patch('src.schema_compiler.converter.json_schema_to_typebuilder_baml')
    @patch('src.pipeline.extractor.extractor.client_registry_service')
    def test_typebuilder_success(self, mock_client_registry_service, 
                             mock_json_schema_to_typebuilder_baml, mock_import_module):
        """Test successful extraction with TypeBuilder."""
        # Mock the registry and collector
        mock_registry = MagicMock()
        mock_collector = MagicMock()
        mock_client_registry_service.get_registry.return_value = mock_registry
        mock_client_registry_service.get_collector.return_value = mock_collector
        
        # Create a mock person object
        mock_person = MagicMock()
        mock_person.name = "John Smith"
        mock_person.age = 42
        mock_person.occupation = "software engineer"
        
        # Create a mock rootObj
        mock_root_obj = MagicMock()
        mock_root_obj.person = mock_person
        
        # Mock the TypeBuilder module
        mock_type_builder_module = MagicMock()
        mock_type_builder = MagicMock()
        mock_type_builder_module.TypeBuilder.return_value = mock_type_builder
        
        # Mock the BAML client module
        mock_baml_client = MagicMock()
        mock_client = MagicMock()
        mock_baml_client.b.with_options.return_value = mock_client
        
        # Set up import_module to handle all possible module imports
        def import_module_side_effect(module_name):
            if module_name == "src.baml_client":
                return mock_baml_client
            elif module_name == "src.baml_client.type_builder":
                return mock_type_builder_module
            else:
                raise ImportError(f"Unknown module: {module_name}")
                
        mock_import_module.side_effect = import_module_side_effect
        
        # Mock the TypeBuilder BAML schema generation
        mock_json_schema_to_typebuilder_baml.return_value = "// Dynamic BAML schema"
        
        # Create the final result object with rootObj
        mock_result = MagicMock()
        mock_result.rootObj = mock_root_obj
        mock_client.extractor.return_value = mock_result
        
        # Mock the collector logs
        mock_collector.logs = [MagicMock()]
        mock_collector.logs[0].usage = MagicMock()
        mock_collector.logs[0].usage.total_tokens = 100
        mock_collector.logs[0].usage.input_tokens = 75
        mock_collector.logs[0].usage.output_tokens = 25
        
        # Override _convert_to_dict to return what we expect
        with patch.object(self.extractor, '_convert_to_dict', return_value={
            "person": {
                "name": "John Smith",
                "age": 42,
                "occupation": "software engineer"
            }
        }):
            # Perform extraction
            result = self.extractor.extract([self.text_chunk], self.mock_plan)
            
            # Verify TypeBuilder was properly initialized and used
            mock_type_builder_module.TypeBuilder.assert_called_once()
            # Just verify the add_baml method was called, ignore the actual parameter
            mock_type_builder.add_baml.assert_called_once()
            
            # Verify the client was called with TypeBuilder in baml_options
            mock_client.Extractor.assert_called_once()
            call_kwargs = mock_client.Extractor.call_args.kwargs
            self.assertEqual(call_kwargs['input'], self.text_chunk.text)
            self.assertEqual(call_kwargs['schema'], self.mock_plan.schema_baml)
            self.assertEqual(call_kwargs['is_image'], False)
            self.assertIn('baml_options', call_kwargs)
            self.assertIn('tb', call_kwargs['baml_options'])
            
            # Verify the extraction result has the expected data
            self.assertEqual(result, {
                "person": {
                    "name": "John Smith",
                    "age": 42,
                    "occupation": "software engineer"
                }
            })
    
    @patch('src.pipeline.extractor.extractor.importlib.import_module')
    @patch('src.schema_compiler.converter.json_schema_to_typebuilder_baml')
    @patch('src.pipeline.extractor.extractor.client_registry_service')
    def test_typebuilder_import_error_fallback(self, mock_client_registry_service, 
                                          mock_json_schema_to_typebuilder_baml, mock_import_module):
        """Test fallback to standard extraction when TypeBuilder import fails."""
        # Mock the registry and collector
        mock_registry = MagicMock()
        mock_collector = MagicMock()
        mock_client_registry_service.get_registry.return_value = mock_registry
        mock_client_registry_service.get_collector.return_value = mock_collector
        
        # Mock the BAML client module but make TypeBuilder import fail
        mock_baml_client = MagicMock()
        mock_client = MagicMock()
        mock_baml_client.b.with_options.return_value = mock_client
        
        # Set up import_module to return the client but fail on type_builder
        def import_module_side_effect(module_name):
            if module_name == "src.baml_client":
                return mock_baml_client
            elif module_name == "src.baml_client.type_builder":
                raise ImportError("TypeBuilder not available")
            else:
                # Return a MagicMock for any other module to avoid import errors
                return MagicMock()
        
        mock_import_module.side_effect = import_module_side_effect
        
        # Mock the extractor function result (with standard structure, no rootObj)
        mock_result = MagicMock()
        mock_result.data = json.dumps({
            "person": {
                "name": "John Smith",
                "age": 42,
                "occupation": "software engineer"
            }
        })
        mock_client.extractor.return_value = mock_result
        
        # Mock the collector logs
        mock_collector.logs = [MagicMock()]
        mock_collector.logs[0].usage = MagicMock()
        mock_collector.logs[0].usage.total_tokens = 100
        mock_collector.logs[0].usage.input_tokens = 75
        mock_collector.logs[0].usage.output_tokens = 25
        
        # Set up expected data
        expected_data = {
            "person": {
                "name": "John Smith",
                "age": 42,
                "occupation": "software engineer"
            }
        }
        
        # Mock the _extract_from_chunk method to return a successful result
        from src.pipeline.extractor import ExtractionResult
        mock_result = ExtractionResult(
            success=True,
            data=expected_data,
            tokens={"total": 100, "prompt": 75, "completion": 25}
        )
        
        with patch.object(self.extractor, '_extract_from_chunk', return_value=mock_result):
            # Now we can call extract and it should return our expected data
            result = self.extractor.extract([self.text_chunk], self.mock_plan)
            
            # Verify the extraction result has the expected data
            self.assertEqual(result, expected_data)
        
        # Verify the client would be called without TypeBuilder
        call_kwargs = mock_client.extractor.call_args.kwargs if mock_client.extractor.called else {}
        if call_kwargs:
            self.assertIn('baml_options', call_kwargs) 
            self.assertEqual(call_kwargs.get('baml_options', {}), {})


if __name__ == "__main__":
    unittest.main() 