#!/usr/bin/env python3
"""
Unit tests for bidirectional conversion between JSON Schema and BAML property names.
"""

import sys
import os
import unittest
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.schema_compiler.converter import json_schema_to_baml, baml_to_json_schema


class TestBidirectionalConversion(unittest.TestCase):
    """Test the bidirectional conversion between JSON Schema and BAML property names."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Example original JSON Schema with hyphenated property names and reserved keywords
        self.original_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "properties": {
                "pre-if": {
                    "type": "boolean",
                    "description": "A condition to check"
                },
                "post-if": {
                    "type": "string",
                    "description": "A post condition"
                },
                "env": {
                    "type": "object",
                    "properties": {
                        "NODE_ENV": {"type": "string"}
                    }
                },
                "class": {  # This is a reserved word in BAML
                    "type": "string",
                    "description": "CSS class"
                }
            }
        }
        
        # Example data with BAML-formatted property names (mimicking LLM output)
        self.baml_data = {
            "pre_if": True,
            "post_if": "success",
            "environment": {
                "NODE_ENV": "production"
            },
            "class_name": "button primary"
        }
    
    def test_forward_conversion(self):
        """Test conversion from JSON Schema to BAML."""
        baml_text = json_schema_to_baml(self.original_schema)
        
        # Basic assertions to verify the conversion worked
        self.assertIn("pre_if bool?", baml_text)
        self.assertIn("post_if string?", baml_text)
        self.assertIn("environment Env?", baml_text)
        self.assertIn("class_name string?", baml_text)
    
    def test_bidirectional_conversion(self):
        """Test bidirectional conversion from JSON Schema to BAML and back."""
        # First, run the forward conversion to set up mappings
        json_schema_to_baml(self.original_schema)
        
        # Then convert back using the reverse mapping
        original_format = baml_to_json_schema(self.baml_data, self.original_schema)
        
        # Verify conversion was successful
        self.assertEqual(original_format["pre-if"], True)
        self.assertEqual(original_format["post-if"], "success")
        self.assertEqual(original_format["env"]["NODE_ENV"], "production")
        self.assertEqual(original_format["class"], "button primary")
    
    def test_nested_properties(self):
        """Test conversion of nested properties."""
        # Define a schema with nested properties
        nested_schema = {
            "properties": {
                "user-info": {
                    "type": "object",
                    "properties": {
                        "first-name": {"type": "string"},
                        "last-name": {"type": "string"},
                        "env": {"type": "string"}
                    }
                }
            }
        }
        
        # Create nested BAML data
        nested_baml_data = {
            "user_info": {
                "first_name": "John",
                "last_name": "Doe",
                "environment": "development"
            }
        }
        
        # Run forward conversion to set up mappings
        json_schema_to_baml(nested_schema)
        
        # Convert back
        original_format = baml_to_json_schema(nested_baml_data, nested_schema)
        
        # Verify nested conversion
        self.assertEqual(original_format["user-info"]["first-name"], "John")
        self.assertEqual(original_format["user-info"]["last-name"], "Doe")
        self.assertEqual(original_format["user-info"]["env"], "development")


if __name__ == "__main__":
    unittest.main() 