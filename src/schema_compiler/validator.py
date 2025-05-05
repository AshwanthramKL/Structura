import jsonschema
from typing import Dict, Any, List, Optional, Tuple, Union, Set
import json
import os

class SchemaValidationError(Exception):
    """Exception raised for schema validation errors with detailed path information."""
    
    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors
        message = f"JSON validation failed with {len(errors)} errors"
        super().__init__(message)


class SchemaValidator:
    """
    JSON Schema validator harness that provides detailed error reporting.
    Uses the jsonschema reference implementation to validate JSON against schemas.
    """
    
    @staticmethod
    def validate(
        instance: Dict[str, Any], 
        schema: Dict[str, Any],
        raise_exception: bool = True
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate a JSON instance against a JSON Schema.
        
        Args:
            instance: The JSON instance to validate
            schema: The JSON Schema to validate against
            raise_exception: Whether to raise an exception on validation failure
            
        Returns:
            Tuple of (is_valid, errors)
            
        Raises:
            SchemaValidationError: If validation fails and raise_exception is True
        """
        # Create a validator instance
        validator = jsonschema.Draft7Validator(schema)
        
        # Collect all errors
        errors = []
        for error in validator.iter_errors(instance):
            # Format path as a dot-separated string
            path = ".".join(str(path_part) for path_part in error.path) if error.path else "root"
            
            # Create error object
            error_obj = {
                "path": path,
                "message": error.message,
                "schema_path": list(error.schema_path),
                "validator": error.validator,
                "validator_value": error.validator_value,
                "instance": error.instance,
            }
            errors.append(error_obj)
        
        is_valid = len(errors) == 0
        
        if not is_valid and raise_exception:
            raise SchemaValidationError(errors)
            
        return is_valid, errors
    
    @staticmethod
    def load_schema_from_file(schema_path: str) -> Dict[str, Any]:
        """
        Load a JSON Schema from a file.
        
        Args:
            schema_path: Path to the schema file
            
        Returns:
            The loaded schema as a dictionary
            
        Raises:
            FileNotFoundError: If the schema file doesn't exist
            json.JSONDecodeError: If the schema is not valid JSON
        """
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
            
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def find_failing_paths(
        instance: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> Set[str]:
        """
        Find all paths in the instance that fail schema validation.
        
        Args:
            instance: The JSON instance to validate
            schema: The JSON Schema to validate against
            
        Returns:
            Set of dot-separated paths that failed validation
        """
        _, errors = SchemaValidator.validate(instance, schema, raise_exception=False)
        return {error["path"] for error in errors}


# Shorthand functions for common operations
def validate_json(
    instance: Dict[str, Any], 
    schema: Dict[str, Any],
    raise_exception: bool = True
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Shorthand for SchemaValidator.validate"""
    return SchemaValidator.validate(instance, schema, raise_exception)

def load_schema(schema_path: str) -> Dict[str, Any]:
    """Shorthand for SchemaValidator.load_schema_from_file"""
    return SchemaValidator.load_schema_from_file(schema_path)
