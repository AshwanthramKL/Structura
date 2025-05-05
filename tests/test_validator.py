import unittest
import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schema_compiler.validator import SchemaValidator, SchemaValidationError

class TestSchemaValidator(unittest.TestCase):
    """Tests for the SchemaValidator component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.github_schema_file = self.data_dir / "github_actions_schema.json"
        self.resume_schema_file = self.data_dir / "convert your resume to this schema.json"
        
        # Ensure test files exist
        self.assertTrue(self.github_schema_file.exists(), f"Test schema file not found: {self.github_schema_file}")
        self.assertTrue(self.resume_schema_file.exists(), f"Test schema file not found: {self.resume_schema_file}")
        
        # Load schema for tests
        self.github_schema = SchemaValidator.load_schema_from_file(str(self.github_schema_file))
    
    def test_load_schema(self):
        """Test loading a schema from file."""
        schema = SchemaValidator.load_schema_from_file(str(self.github_schema_file))
        self.assertIsInstance(schema, dict)
        self.assertIn("$schema", schema)
        self.assertIn("properties", schema)
    
    def test_valid_json(self):
        """Test validating a valid JSON instance."""
        # Create a minimal valid GitHub Action
        valid_instance = {
            "name": "Test Action",
            "description": "This is a test action",
            "runs": {
                "using": "node12",
                "main": "index.js"
            }
        }
        
        is_valid, errors = SchemaValidator.validate(valid_instance, self.github_schema, raise_exception=False)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_json(self):
        """Test validating an invalid JSON instance."""
        # Create an invalid GitHub Action (missing required 'main' field)
        invalid_instance = {
            "name": "Test Action",
            "description": "This is a test action",
            "runs": {
                "using": "node12"
                # Missing 'main' field
            }
        }
        
        # Test with no exception
        is_valid, errors = SchemaValidator.validate(invalid_instance, self.github_schema, raise_exception=False)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # jsonschema doesn't always provide a clear error message specifically mentioning 'main'
        # Let's just verify it's reporting an error on the 'runs' object
        self.assertIn("runs", errors[0]["path"])
        
        # Test with exception
        with self.assertRaises(SchemaValidationError) as context:
            SchemaValidator.validate(invalid_instance, self.github_schema, raise_exception=True)
        
        self.assertGreater(len(context.exception.errors), 0)
    
    def test_multiple_validation_errors(self):
        """Test validating a JSON instance with multiple validation errors."""
        # Create an instance with multiple validation errors
        invalid_instance = {
            "name": 12345,  # Should be a string
            "description": "This is a test action",
            "inputs": {
                "test-input": {
                    "required": "not-a-boolean"  # Should be a boolean
                }
            },
            "runs": {
                "using": "invalid-runtime",  # Invalid enum value
                # Missing 'main' field
            },
            "invalid-field": "This field doesn't exist in the schema"  # Additional property not allowed
        }
        
        # Validate with no exception
        is_valid, errors = SchemaValidator.validate(invalid_instance, self.github_schema, raise_exception=False)
        
        # Assertions
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 1, "Should detect multiple errors")
        
        # Collect all error paths
        error_paths = [error["path"] for error in errors]
        
        # Verify that multiple distinct paths were detected
        unique_paths = set(error_paths)
        self.assertGreater(len(unique_paths), 1, "Should have errors at multiple paths")
        
        # Print the paths for debugging
        print(f"Detected error paths: {unique_paths}")
        
        # Verify the exception contains all errors
        with self.assertRaises(SchemaValidationError) as context:
            SchemaValidator.validate(invalid_instance, self.github_schema, raise_exception=True)
        
        self.assertEqual(len(context.exception.errors), len(errors), 
                         "Exception should contain all validation errors")
    
    def test_find_failing_paths(self):
        """Test finding all failing paths in a JSON instance."""
        # Create an invalid instance with multiple issues
        invalid_instance = {
            "name": 12345,  # Should be a string
            "description": "This is a test action",
            "runs": {
                "using": "invalid-runtime",  # Invalid enum value
                # Missing 'main' field
            }
        }
        
        failing_paths = SchemaValidator.find_failing_paths(invalid_instance, self.github_schema)
        self.assertIsInstance(failing_paths, set)
        self.assertGreater(len(failing_paths), 0)
        
        # Check if specific paths are detected
        # jsonschema may report the issue at the object level rather than the specific property
        self.assertIn("name", failing_paths)
        self.assertIn("runs", failing_paths)
    
    def test_detailed_error_format(self):
        """Test the detailed error format returned by the validator."""
        invalid_instance = {
            "name": 12345,  # Should be a string
            "description": "This is a test action",
            "runs": {
                "using": "invalid-runtime",  # Invalid enum value
                # Missing 'main' field
            }
        }
        
        _, errors = SchemaValidator.validate(invalid_instance, self.github_schema, raise_exception=False)
        
        for error in errors:
            self.assertIn("path", error)
            self.assertIn("message", error)
            self.assertIn("schema_path", error)
            self.assertIn("validator", error)
            self.assertIn("validator_value", error)
            self.assertIn("instance", error)


if __name__ == "__main__":
    unittest.main() 