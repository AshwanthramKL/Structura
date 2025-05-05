import unittest
import json
import os
from pathlib import Path
from src.schema_compiler.converter import json_schema_to_baml

FIXTURES_DIR = Path(__file__).parent / "schema_compiler" / "fixtures"
DATA_DIR = Path(__file__).parent.parent / "data"
TEMP_BAML_DIR = Path(__file__).parent.parent / "temp_baml"

class TestSchemaCompiler(unittest.TestCase):
    """Main unit tests for the JSON Schema → BAML compiler.
    Note: More comprehensive tests are in tests/schema_compiler/test_baml_converter.py"""

    def setUp(self):
        """Ensure temp directory exists."""
        os.makedirs(TEMP_BAML_DIR, exist_ok=True)

    def _compile(self, fixture_name: str) -> str:
        """Compile a schema from fixtures and return the BAML text."""
        path = FIXTURES_DIR / f"{fixture_name}.json"
        schema = json.loads(path.read_text())
        baml = json_schema_to_baml(schema)
        
        # Save the output to temp directory
        output_file = TEMP_BAML_DIR / f"{fixture_name}.baml"
        output_file.write_text(baml)
        
        return baml

    def _compile_data(self, filename: str) -> str:
        """Compile a schema from data directory and return the BAML text."""
        path = DATA_DIR / filename
        schema = json.loads(path.read_text())
        baml = json_schema_to_baml(schema)
        
        # Save the output to temp directory
        base_name = Path(filename).stem
        output_file = TEMP_BAML_DIR / f"{base_name}.baml"
        output_file.write_text(baml)
        
        return baml

    def test_root_metadata_ignored(self):
        baml = self._compile("root_meta")
        self.assertNotIn("$schema", baml)
        self.assertNotIn("$id", baml)
        self.assertIn("class Root", baml)

    def test_pattern_properties_fallback(self):
        baml = self._compile("pattern_props")
        self.assertIn("patternProperties fallback", baml)
        # Verify the pattern properties are included in comments
        self.assertIn("^x-", baml)
        self.assertIn("^custom_[0-9]+$", baml)

    def test_enum_large_comment(self):
        baml = self._compile("large_enum")
        # Check for enum definition
        self.assertIn("enum CountryCodeenum", baml)
        # Check for enum values
        self.assertIn("AF", baml)
        self.assertIn("CU", baml)

    def test_numeric_min_max(self):
        baml = self._compile("numeric_range")
        # Check for min/max in description instead of @min/@max
        self.assertIn("Min: 0", baml)
        self.assertIn("Max: 10", baml)
        self.assertIn("Max: 120", baml)

    def test_array_items(self):
        baml = self._compile("array_items")
        # Check array syntax
        self.assertIn("string[]", baml)
        self.assertIn("float[]", baml)

    def test_unknown_keyword(self):
        baml = self._compile("unknown_kw")
        # Check for proper type 
        self.assertIn("email", baml)
        self.assertIn("string", baml)

    def test_references(self):
        baml = self._compile("ref")
        # Check for proper class case
        self.assertIn("class Address", baml)
        self.assertIn("class Root", baml)
        # Check that $ref was resolved
        self.assertIn("homeAddress", baml)
        self.assertIn("workAddress", baml)
        # Check that the required field settings are respected
        self.assertIn("street string", baml)  # No ? = required
        self.assertIn("zip string?", baml)  # With ? = optional

    def test_union_types(self):
        baml = self._compile("union")
        # Check oneOf handling
        self.assertIn('"pending" | "active" | "inactive" | int', baml) 
        # Check type union
        self.assertIn("string | string | Contact", baml)
        # Check nested class creation
        self.assertIn("class Contact", baml) 

    def test_nested_object_structure(self):
        baml = self._compile("nested")
        # Check for nested class definitions
        self.assertIn("company", baml)
        self.assertIn("department", baml)
        self.assertIn("team", baml)
        self.assertIn("members", baml)
        # Check for array handling in nested structure
        self.assertIn("members", baml)
        self.assertIn("skills", baml)

    def test_complex_types(self):
        baml = self._compile("complex_types")
        # Check handling of multiple types in type array
        self.assertIn("id", baml)
        self.assertIn("string | int", baml)
        # Check handling of array with oneOf for items
        self.assertIn("mixedArray", baml)

    # Test real-world examples from data directory
    def test_github_actions_schema(self):
        baml = self._compile_data("github_actions_schema.json")
        # Verify basic structure was created
        self.assertIn("class Root", baml)
        # Ensure no validation errors
        self.assertNotIn("ERROR:", baml)
        
        # Save to the temp_baml directory for manual inspection
        with open(TEMP_BAML_DIR / "github_actions_schema.baml", "w") as f:
            f.write(baml)

    def test_paper_citations_schema(self):
        baml = self._compile_data("paper citations_schema.json")
        # Verify basic structure was created
        self.assertIn("class Root", baml)
        # Ensure no validation errors
        self.assertNotIn("ERROR:", baml)
        
        # Save to the temp_baml directory for manual inspection
        with open(TEMP_BAML_DIR / "paper_citations_schema.baml", "w") as f:
            f.write(baml)

    def test_resume_schema(self):
        baml = self._compile_data("convert your resume to this schema.json")
        # Verify basic structure was created
        self.assertIn("class Root", baml)
        # Ensure no validation errors
        self.assertNotIn("ERROR:", baml)
        
        # Save to the temp_baml directory for manual inspection
        with open(TEMP_BAML_DIR / "resume_schema.baml", "w") as f:
            f.write(baml)


if __name__ == "__main__":
    unittest.main()
