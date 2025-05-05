#!/usr/bin/env python3
"""
Tests for the JSON Schema to BAML converter.
Includes tests for edge cases, basic validation, and integration.
"""

import json
import os
import subprocess
import tempfile
import unittest
from dotenv import load_dotenv
from pathlib import Path
from src.schema_compiler.converter import json_schema_to_baml

# Load environment variables from .env file
load_dotenv()

# Set up test paths
TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / "fixtures"
TEMP_OUTPUT_DIR = Path(tempfile.mkdtemp())

class ConverterTestCase(unittest.TestCase):
    """Base class for converter tests with common utilities."""
    
    def validate_baml(self, baml_file):
        """Validate a BAML file using baml-cli fmt command."""
        try:
            cmd = ['baml-cli', 'fmt', '--dry-run', baml_file]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                check=False
            )
            return result.returncode == 0, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)
    
    def format_baml_value(self, value):
        """Format a Python value as a BAML value."""
        if isinstance(value, str):
            # Escape quotes in strings
            escaped_value = value.replace('"', '\\"')
            return f'"{escaped_value}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif value is None:
            return "null"
        elif isinstance(value, list):
            formatted_items = []
            for item in value:
                if isinstance(item, dict):
                    nested_dict = self.format_nested_dict(item, indent=8)
                    formatted_items.append(f"{{\n{nested_dict}\n      }}")
                else:
                    formatted_items.append(self.format_baml_value(item))
            return f"[\n      {', '.join(formatted_items)}\n    ]"
        elif isinstance(value, dict):
            # Format the dictionary with proper indentation
            return f"{{\n{self.format_nested_dict(value, indent=6)}\n  }}"
        else:
            raise ValueError(f"Unsupported type: {type(value)}")
    
    def format_nested_dict(self, d, indent=4):
        """Format a nested dictionary with the specified indentation."""
        spaces = " " * indent
        lines = []
        for key, val in d.items():
            if isinstance(val, dict):
                nested_dict = self.format_nested_dict(val, indent + 4)
                lines.append(f"{spaces}{key} {{\n{nested_dict}\n{spaces}}}")
            elif isinstance(val, list):
                formatted_list = self.format_baml_value(val).replace("\n", f"\n{spaces}")
                lines.append(f"{spaces}{key} {formatted_list}")
            else:
                lines.append(f"{spaces}{key} {self.format_baml_value(val)}")
        return "\n".join(lines)
    
    def add_test_cases_to_baml(self, baml_content, test_inputs, function_name):
        """Add test cases to validate the BAML output."""
        # First, add a test function that uses the classes
        baml_content += f"""
function Test{function_name}(input: {function_name}) -> {function_name} {{
  client "openai/gpt-4o"
  
  prompt #"
    This is a validation function.
    Simply return the input object as is.
    
    Input:
    {{{{ input }}}}
    
    {{{{ ctx.output_format }}}}
  "#
}}

"""
        
        # Add test cases for each test input
        for i, test_input in enumerate(test_inputs):
            test_name = test_input["name"]
            test_data = test_input["data"]
            formatted_input = self.format_baml_value(test_data)
            
            baml_content += f"""
test {test_name}_test {{
  functions [Test{function_name}]
  args {{
    input {formatted_input}
  }}
  @@check(valid_result, {{{{ this is defined }}}})
  @@assert({{{{ _.checks.valid_result }}}})
}}

"""
        
        return baml_content


class TestBasicConversion(ConverterTestCase):
    """Test basic conversion of JSON schemas to BAML."""
    
    def test_simple_schema(self):
        """Test converting a simple JSON schema to BAML."""
        # Load the test schema
        with open(FIXTURES_DIR / "simple.json", "r") as f:
            schema = json.load(f)
        
        # Convert to BAML
        baml_output = json_schema_to_baml(schema, "Person")
        
        # Create test cases
        test_inputs = [
            {
                "name": "complete_person", 
                "data": {
                    "name": "John Doe",
                    "age": 30,
                    "email": "john.doe@example.com",
                    "is_active": True
                }
            },
            {
                "name": "minimal_person",
                "data": {
                    "name": "Jane Smith",
                    "age": 25
                }
            }
        ]
        
        # Add test cases to BAML
        baml_output = self.add_test_cases_to_baml(baml_output, test_inputs, "Person")
        
        # Write to a file for validation
        output_file = TEMP_OUTPUT_DIR / "simple.baml"
        with open(output_file, "w") as f:
            f.write(baml_output)
        
        # Validate the BAML
        is_valid, error = self.validate_baml(output_file)
        self.assertTrue(is_valid, f"Simple schema validation failed: {error}")
    
    def test_complex_schema(self):
        """Test converting a complex JSON schema with nested objects to BAML."""
        # Load the test schema
        with open(FIXTURES_DIR / "complex.json", "r") as f:
            schema = json.load(f)
        
        # Convert to BAML
        baml_output = json_schema_to_baml(schema, "Organization")
        
        # Create test cases
        test_inputs = [
            {
                "name": "tech_company",
                "data": {
                    "name": "TechCorp",
                    "year_founded": 2005,
                    "industry": "Technology",
                    "headquarters": {
                        "street": "123 Tech Blvd",
                        "city": "San Francisco",
                        "country": "US"
                    },
                    "employees": [
                        {
                            "id": "E001",
                            "name": "Alice Johnson",
                            "department": "Engineering"
                        }
                    ],
                    "active": True
                }
            }
        ]
        
        # Add test cases to BAML
        baml_output = self.add_test_cases_to_baml(baml_output, test_inputs, "Organization")
        
        # Write to a file for validation
        output_file = TEMP_OUTPUT_DIR / "complex.baml"
        with open(output_file, "w") as f:
            f.write(baml_output)
        
        # Validate the BAML
        is_valid, error = self.validate_baml(output_file)
        self.assertTrue(is_valid, f"Complex schema validation failed: {error}")


class TestEdgeCases(ConverterTestCase):
    """Test edge cases of the JSON Schema to BAML converter."""
    
    def _test_edge_case(self, case_name, schema):
        """Test a single edge case and validate the BAML output."""
        try:
            # Convert schema to BAML
            baml_output = json_schema_to_baml(schema, f"{case_name.capitalize()}Root")
            
            # Write BAML to a temporary file
            output_file = TEMP_OUTPUT_DIR / f"{case_name}.baml"
            with open(output_file, "w") as f:
                f.write(baml_output)
            
            # Validate BAML syntax
            is_valid, error = self.validate_baml(output_file)
            self.assertTrue(is_valid, f"{case_name} validation failed: {error}")
            
            return True
        except Exception as e:
            self.fail(f"Error in {case_name} edge case: {str(e)}")
            return False
    
    def test_nested_objects(self):
        """Test schema with deeply nested objects."""
        schema = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "level2": {
                            "type": "object",
                            "properties": {
                                "level3": {
                                    "type": "object",
                                    "properties": {
                                        "value": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        self._test_edge_case("nested_objects", schema)
    
    def test_complex_arrays(self):
        """Test schema with complex array structures."""
        schema = {
            "type": "object",
            "properties": {
                "arrayOfObjects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "values": {
                                "type": "array",
                                "items": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        }
        self._test_edge_case("complex_arrays", schema)
    
    def test_union_types(self):
        """Test schema with union types."""
        schema = {
            "type": "object",
            "properties": {
                "unionField": {
                    "type": ["string", "integer", "null"]
                },
                "oneOfField": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "object", "properties": {"value": {"type": "integer"}}}
                    ]
                }
            }
        }
        self._test_edge_case("union_types", schema)
    
    def test_references(self):
        """Test schema with references."""
        schema = {
            "type": "object",
            "properties": {
                "refField": {"$ref": "#/definitions/RefType"}
            },
            "definitions": {
                "RefType": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "recursive": {"$ref": "#/definitions/RefType"}
                    }
                }
            }
        }
        self._test_edge_case("references", schema)
    
    def test_pattern_properties(self):
        """Test schema with pattern properties."""
        schema = {
            "type": "object",
            "patternProperties": {
                "^[a-z]+$": {"type": "string"},
                "^[0-9]+$": {"type": "integer"}
            }
        }
        self._test_edge_case("pattern_properties", schema)
    
    def test_large_enum(self):
        """Test schema with large enum."""
        large_enum = [f"Value{i}" for i in range(100)]
        schema = {
            "type": "object",
            "properties": {
                "largeEnum": {
                    "type": "string",
                    "enum": large_enum
                }
            }
        }
        self._test_edge_case("large_enum", schema)


class TestIntegration(ConverterTestCase):
    """Test full integration with BAML CLI tools."""
    
    def test_integration(self):
        """Test full integration with BAML CLI."""
        # Skip if environment is not set up for full BAML testing
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY not set, skipping full integration test")
        
        try:
            # Create temporary test directory
            test_dir = Path(tempfile.mkdtemp())
            
            # Create directories
            baml_src_dir = test_dir / "baml_src"
            baml_src_dir.mkdir(exist_ok=True)
            
            # Get OpenAI API key from environment
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            
            # Create clients.baml
            clients_content = f"""
client<llm> TestClient {{
  provider openai
  options {{
    model gpt-4o
    api_key "{openai_api_key}"
    temperature 0
  }}
}}
"""
            with open(baml_src_dir / "clients.baml", "w") as f:
                f.write(clients_content)
            
            # Create empty generators.baml
            with open(baml_src_dir / "generators.baml", "w") as f:
                f.write("// Test generators file\n")
            
            # Create test schema
            schema = {
                "type": "object",
                "title": "Person",
                "properties": {
                    "name": {"type": "string", "description": "Full name of the person"},
                    "age": {"type": "integer", "minimum": 0, "maximum": 120},
                    "email": {"type": "string", "format": "email"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "zipCode": {"type": "string"}
                        },
                        "required": ["street", "city"]
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["name", "age"]
            }
            
            # Convert schema to BAML
            baml_content = json_schema_to_baml(schema, "Person")
            
            # Add a test function
            baml_content += f"""
function TestPerson(input: Person) -> Person {{
  client TestClient
  
  prompt #"
    This is a test function that simply returns the input object as-is.
    
    Input:
    {{{{ input }}}}
    
    {{{{ ctx.output_format }}}}
  "#
}}

"""
            
            # Add test cases
            test_cases = [
                {
                    "name": "person_complete",
                    "input": {
                        "name": "John Doe",
                        "age": 30,
                        "email": "john@example.com",
                        "address": {
                            "street": "123 Main St",
                            "city": "New York",
                            "zipCode": "10001"
                        },
                        "tags": ["developer", "new-york"]
                    }
                },
                {
                    "name": "person_minimal",
                    "input": {
                        "name": "Jane Smith",
                        "age": 25
                    }
                }
            ]
            
            for test_case in test_cases:
                test_name = test_case["name"]
                input_data = test_case["input"]
                
                # Format input data in BAML syntax
                formatted_input = self.format_baml_value(input_data)
                
                baml_content += f"""
test {test_name} {{
  functions [TestPerson]
  args {{
    input {formatted_input}
  }}
  @@check(valid_result, {{{{ this is defined }}}})
  @@assert({{{{ _.checks.valid_result }}}})
}}

"""
            
            # Write the BAML file
            baml_file_path = baml_src_dir / "person.baml"
            with open(baml_file_path, "w") as f:
                f.write(baml_content)
            
            # Generate BAML client code
            generate_cmd = ["baml-cli", "generate"]
            generate_result = subprocess.run(
                generate_cmd,
                cwd=test_dir,
                capture_output=True,
                text=True,
                check=False
            )
            self.assertEqual(generate_result.returncode, 0, 
                             f"Failed to generate BAML client code: {generate_result.stderr}")
            
            # Run BAML tests
            test_cmd = ["baml-cli", "test"]
            test_result = subprocess.run(
                test_cmd,
                cwd=test_dir,
                capture_output=True,
                text=True,
                check=False
            )
            self.assertEqual(test_result.returncode, 0,
                            f"BAML tests failed: {test_result.stderr}")
            
        except Exception as e:
            self.fail(f"Integration test failed: {str(e)}")


if __name__ == "__main__":
    unittest.main() 