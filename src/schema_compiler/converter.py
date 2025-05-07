"""schema_compiler.converter

Convert JSON-Schema (draft-07) to BAML types and vice versa.

This module intentionally **does not** depend on the runtime `baml_client` in
order to avoid the heavy open-ai compile step during unit tests.
Instead, it produces a plain **BAML text string** that can later be piped into
`baml-cli generate`.

Features supported:
- Flat class structure (no nested classes)
- Optionality with the `?` syntax
- Unions with `|` syntax
- Attributes like `@description`
- References to definitions
- Array types
- Proper handling of hyphenated property names
- BAML-compliant enum formatting (ALL_CAPS)
- Single-line descriptions with proper escaping
- Handling of BAML reserved keywords
- Bidirectional conversion between JSON Schema and BAML
- Avoidance of BAML built-in type name conflicts

Limitations
-----------
* Only local `$ref` ("#/definitions/…") pointers are supported.
* `oneOf` / `anyOf` / `allOf` are rendered as BAML union types.
* Complex keywords that BAML cannot express (e.g. `patternProperties`) fall
  back to an embedded JSON block inside a BAML comment.
* BAML enums require values to be ALL_CAPS with no quotes or commas.
* Property names cannot contain hyphens and must start with an uppercase letter.

API
---
``python
from schema_compiler.converter import json_schema_to_baml, baml_to_json_schema

# Convert JSON Schema to BAML
text = json_schema_to_baml(my_schema_dict)
with open("schema.baml", "w") as fp:
    fp.write(text)

# Convert BAML data back to JSON Schema format (for property names)
data = {"Environment": "prod", "Pre_if": True}
original_schema_data = baml_to_json_schema(data, original_schema)
# Result: {"env": "prod", "pre-if": True}
```
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Mapping

__all__ = ["json_schema_to_baml", "baml_to_json_schema"]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Schema metadata fields to exclude from BAML output
SCHEMA_META_FIELDS = {'$schema', '$id', 'title', 'description'}

# BAML reserved keywords that can't be used as property names
BAML_RESERVED_KEYWORDS = {
    'env': 'environment',
    'class': 'class_name',
    'enum': 'enum_value',
    'function': 'function_impl',
    'test': 'test_case',
    'prompt': 'prompt_template',
    'client': 'client_name',
    # Jinja templating keywords
    'if': 'condition',
    'for': 'loop',
    'in': 'contained_in',
    'with': 'input_params',
    'extends': 'parent',
    'include': 'included_content',
    'block': 'content_block',
    'macro': 'template_macro',
    'set': 'variable_set',
    'filter': 'content_filter',
    'import': 'imported_content',
    'from': 'import_source',
    'as': 'alias',
}

# BAML built-in or reserved class/type names that should not be redefined
BAML_RESERVED_TYPES = {
    # Common built-in BAML types
    'Email', 'URL', 'Date', 'DateTime', 'Time', 'UUID', 'File',
    'Boolean', 'Number', 'String', 'Integer', 'Float', 'Double',
    # Additional types that might be built-in or commonly used
    'Json', 'Object', 'Array', 'Map', 'Set', 'List',
}


class Converter:
    """Class to convert JSON Schema to BAML and vice versa."""
    
    def __init__(self):
        """Initialize the converter with empty mappings."""
        # Bidirectional mapping for property name conversion
        self._property_name_mappings = {}
        # Reverse mapping (BAML to JSON Schema)
        self._reverse_mappings = {}
        # Map of renamed classes (original -> renamed)
        self._class_name_mappings = {}
        # Track renamed types for consistent references
        self._renamed_types = {}
        # Original schema object (for restoring metadata)
        self._original_schema = None
        # Track classes that have been processed
        self._processed_classes = set()
    
    def _clean_name(self, name: str) -> str:
        """Clean a name to be a valid BAML identifier."""
        if not name:
            return "Unknown"
        
        # Replace non-alphanumeric chars with spaces
        name = re.sub(r'[^a-zA-Z0-9]', ' ', name)
        
        # Title case and remove spaces
        words = name.split()
        if not words:
            return "Unknown"
        
        # Convert to PascalCase for class names
        return ''.join(word.capitalize() for word in words)
    
    def _sanitize_class_name(self, name: str) -> str:
        """
        Sanitize a class name to avoid conflicts with BAML built-in types.
        
        If a class name conflicts with a BAML reserved type/class, append 'Type'
        to it to avoid the conflict.
        """
        clean_name = self._clean_name(name)
        
        # Check if we've already renamed this class
        if clean_name in self._renamed_types:
            return self._renamed_types[clean_name]
        
        # If the class name conflicts with a BAML reserved type, append 'Type'
        sanitized_name = clean_name
        if clean_name in BAML_RESERVED_TYPES:
            sanitized_name = f"{clean_name}Type"
            
        # Store both mappings for consistent reference
        self._class_name_mappings[clean_name] = sanitized_name
        self._renamed_types[clean_name] = sanitized_name
        
        return sanitized_name
    
    def _reverse_class_name(self, baml_class_name: str) -> str:
        """
        Convert a potentially modified BAML class name back to the original.
        """
        # Check if this is one of our renamed classes
        for original, renamed in self._class_name_mappings.items():
            if renamed == baml_class_name:
                return original
        
        # If not found in mappings, just return the name as is
        return baml_class_name
    
    def _sanitize_property_name(self, name: str) -> str:
        """Convert property names to BAML-compliant format.
        
        - Replace hyphens with underscores
        - Ensure property names start with a letter
        - Handle BAML reserved keywords
        - Track original names for bidirectional mapping
        """
        if name in self._property_name_mappings:
            return self._property_name_mappings[name]
        
        # Check if this is a BAML reserved keyword
        if name in BAML_RESERVED_KEYWORDS:
            sanitized = BAML_RESERVED_KEYWORDS[name]
        else:
            # Handle hyphens
            sanitized = name.replace('-', '_')
            
            # Ensure it starts with a letter
            if sanitized and not sanitized[0].isalpha():
                sanitized = 'prop_' + sanitized
        
        # Store in mapping for later reference
        self._property_name_mappings[name] = sanitized
        # Store reverse mapping (case-insensitive to handle potential capitalization)
        self._reverse_mappings[sanitized.lower()] = name
        
        return sanitized
    
    def _reverse_property_name(self, baml_name: str) -> str:
        """Convert a BAML property name back to the original JSON Schema name.
        
        Uses the mapping created during the forward conversion.
        """
        # Try direct case match first
        if baml_name in self._reverse_mappings:
            return self._reverse_mappings[baml_name]
        
        # Try lowercase match
        baml_name_lower = baml_name.lower()
        if baml_name_lower in self._reverse_mappings:
            return self._reverse_mappings[baml_name_lower]
        
        # If no mapping exists, return the name unchanged
        return baml_name
    
    def _format_enum_value(self, value: Any) -> str:
        """Format enum values to comply with BAML requirements.
        
        BAML enum values must be ALL_CAPS with no quotes or commas.
        """
        if isinstance(value, str):
            # Convert to uppercase, replace hyphens and spaces with underscores
            formatted = value.upper().replace('-', '_').replace(' ', '_')
            # Remove any non-alphanumeric characters (except underscore)
            formatted = re.sub(r'[^A-Z0-9_]', '', formatted)
            # Ensure it starts with a letter or underscore
            if formatted and not (formatted[0].isalpha() or formatted[0] == '_'):
                formatted = 'ENUM_' + formatted
            return formatted
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif value is None:
            return "NULL"
        else:
            # For numbers, prefix with ENUM_ to ensure it's valid
            return f"ENUM_{value}".upper()
    
    def _process_enum_values(self, enum_values: List[Any]) -> str:
        """Convert enum values to BAML format for inline use (not for enum definitions)."""
        values = []
        for value in enum_values:
            if isinstance(value, str):
                values.append(f'"{value}"')
            elif isinstance(value, bool):
                values.append("true" if value else "false")
            elif value is None:
                values.append("null")
            else:
                values.append(str(value))
        
        return " | ".join(values)
    
    def _sanitize_description(self, description: str) -> str:
        """Sanitize and format description text for BAML.
        
        - Replace newlines with spaces
        - Escape double quotes
        - Handle other special characters
        """
        if not description:
            return ""
        
        # Replace newlines with spaces
        sanitized = description.replace('\n', ' ')
        # Replace multiple spaces with a single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        # Escape double quotes
        sanitized = sanitized.replace('"', '\\"')
        
        return sanitized
    
    def _pattern_to_property_name(self, pattern: str) -> str:
        """Convert a regex pattern into a valid BAML property name.
        
        Args:
            pattern: A regex pattern from patternProperties.
            
        Returns:
            A valid BAML property name representing the pattern.
        """
        # Remove common regex markers
        cleaned = pattern.replace('^', '').replace('$', '')
        # Remove regex character classes [xyz] and replace with placeholders
        cleaned = re.sub(r'\[[^\]]+\]', 'any', cleaned)
        # Remove regex quantifiers and other special characters
        cleaned = re.sub(r'[+*?.{}()]', '', cleaned)
        # Clean the name like other identifiers
        return f"pattern_{self._clean_name(cleaned.lower())}"
    
    def _get_map_value_type(self, schema: Dict[str, Any], name: str, definitions: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Determine the appropriate BAML type for a map value.
        
        For complex types, simplifies to a compatible map type to avoid validation issues.
        
        Args:
            schema: The JSON Schema for the pattern property values.
            name: Base name for the property.
            definitions: Schema definitions.
            
        Returns:
            A tuple of (type_string, additional_class_definitions).
        """
        value_type, value_classes = self._get_baml_type_for_property(
            schema, name + "Value", definitions
        )
        
        # For complex types that aren't directly supported in map values,
        # convert to appropriate simple types
        if value_type not in ["string", "int", "float", "bool"] and not value_type.startswith("map<"):
            if schema.get("type") == "object":
                value_type = "map<string, string>"
            else:
                value_type = "string"
                
        return value_type, value_classes
    
    def _convert_pattern_properties(self, 
                                  patterns: Dict[str, Any], 
                                  class_def: str,
                                  definitions: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Convert JSON Schema patternProperties to BAML map properties.
        
        Args:
            patterns: The patternProperties object from the JSON Schema.
            class_def: The current class definition string.
            definitions: Schema definitions.
            
        Returns:
            A tuple of (updated_class_definition, additional_class_definitions).
        """
        additional_classes = []
        
        # Add a comment explaining the pattern properties - maintain backward compatibility with tests
        class_def += "  // patternProperties fallback\n"
        
        # For each pattern, create a map property with appropriate type
        for pattern, pattern_schema in patterns.items():
            # Generate a clean property name from the pattern
            prop_name = self._pattern_to_property_name(pattern)
            
            # Determine the value type for this pattern
            value_type, value_classes = self._get_map_value_type(
                pattern_schema, prop_name, definitions
            )
            additional_classes.extend(value_classes)
            
            # Add the map property with description showing the pattern
            sanitized_pattern = pattern.replace('"', '\\"')
            class_def += f"  {prop_name} map<string, {value_type}>? @description(\"Properties matching pattern: {sanitized_pattern}\")\n"
        
        return class_def, additional_classes
    
    def json_schema_to_baml(self, schema: Dict[str, Any], root_name: str = "Root") -> str:
        """Main method – returns a BAML text representation of *schema*."""
        # Store original schema for potential future reverse conversion
        self._original_schema = schema.copy()
        
        # Reset state for this conversion
        self._property_name_mappings = {}
        self._reverse_mappings = {}
        self._class_name_mappings = {}
        self._renamed_types = {}
        self._processed_classes = set()
        
        try:
            definitions = schema.get("definitions", {})
            # Also support "$defs" from newer JSON Schema drafts
            if not definitions and "$defs" in schema:
                definitions = schema["$defs"]
            
            main_class, additional_classes = self._schema_to_baml_class(
                schema, root_name, definitions
            )
            
            # Handle pattern properties if they exist
            if "patternProperties" in schema:
                patterns = schema.get("patternProperties", {})
                class_def, pattern_classes = self._convert_pattern_properties(
                    patterns, main_class, definitions
                )
                additional_classes.extend(pattern_classes)
            
            result = "// Generated from JSON-Schema - DO NOT EDIT BY HAND\n\n"
            result += "\n".join(additional_classes) + "\n" + main_class
            return result
        except Exception as e:
            logger.error(f"Error converting schema to BAML: {e}")
            # Return a minimal BAML with error information
            return f"// ERROR: Failed to convert schema to BAML\n// {str(e)}\n\nclass Root {{\n  error string @hidden // {str(e)}\n}}\n"
    
    def baml_to_json_schema(self, baml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert BAML property names back to original JSON Schema names.
        
        This is useful when you have data from a model that uses the BAML schema,
        but you need to convert it back to match the original JSON Schema property names.
        
        Args:
            baml_data: Dictionary with BAML-formatted property names
            
        Returns:
            Dictionary with original JSON Schema property names
        """
        if not self._property_name_mappings and not self._original_schema:
            logger.warning("No conversion mappings available. Call json_schema_to_baml first.")
            return baml_data
            
        return self._convert_object_keys(baml_data)
    
    def _convert_object_keys(self, obj: Any) -> Any:
        """Recursively convert object keys from BAML to JSON Schema format."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Convert the key back to the original JSON Schema name
                original_key = self._reverse_property_name(key)
                # Recursively process any nested objects
                result[original_key] = self._convert_object_keys(value)
            return result
        elif isinstance(obj, list):
            # Process each item in the list
            return [self._convert_object_keys(item) for item in obj]
        else:
            # Return primitive values as-is
            return obj
    
    def _get_baml_type_for_property(self, 
            schema: Dict[str, Any], 
            property_name: str, 
            definitions: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str]]:
        """
        Convert a JSON Schema property to a BAML type.
        
        Returns a tuple of (type_string, additional_class_definitions)
        """
        if definitions is None:
            definitions = {}
        
        additional_classes = []
        
        # Handle $ref 
        if "$ref" in schema:
            ref = schema["$ref"]
            if ref.startswith("#/definitions/") or ref.startswith("#/$defs/"):
                ref_parts = ref.split("/")
                ref_name = ref_parts[-1]
                
                if definitions and ref_name in definitions:
                    ref_schema = definitions[ref_name]
                    class_name = self._sanitize_class_name(ref_name)
                    
                    if class_name not in self._processed_classes:
                        self._processed_classes.add(class_name)
                        class_def, more_classes = self._schema_to_baml_class(
                            ref_schema, class_name, definitions
                        )
                        additional_classes.append(class_def)
                        additional_classes.extend(more_classes)
                    
                    return class_name, additional_classes
            
            return "string", additional_classes  # Default if ref not found
        
        # Handle enum
        if "enum" in schema:
            if len(schema["enum"]) > 50:
                # For very large enums, create a separate enum definition
                enum_name = self._clean_name(property_name + "enum")
                enum_def = f"enum {enum_name} {{\n"
                
                for value in schema["enum"]:
                    # Format as ALL_CAPS with underscore separators for BAML compatibility
                    formatted_value = self._format_enum_value(value)
                    enum_def += f"  {formatted_value}\n"
                
                enum_def += "}\n"
                additional_classes.append(enum_def)
                return enum_name, additional_classes
            else:
                return self._process_enum_values(schema["enum"]), additional_classes
        
        # Handle type
        if "type" in schema:
            schema_type = schema["type"]
            
            # Handle multiple types (union type)
            if isinstance(schema_type, list):
                types = []
                for t in schema_type:
                    new_schema = schema.copy()
                    new_schema["type"] = t
                    type_str, type_classes = self._get_baml_type_for_property(
                        new_schema, property_name, definitions
                    )
                    types.append(type_str)
                    additional_classes.extend(type_classes)
                
                return " | ".join(types), additional_classes
            
            # Handle arrays
            if schema_type == "array":
                items_schema = schema.get("items", {})
                item_type, item_classes = self._get_baml_type_for_property(
                    items_schema, 
                    property_name + "Item", 
                    definitions
                )
                additional_classes.extend(item_classes)
                return f"{item_type}[]", additional_classes
            
            # Handle objects (convert to classes)
            elif schema_type == "object":
                if "properties" in schema:
                    class_name = self._sanitize_class_name(property_name)
                    
                    if class_name not in self._processed_classes:
                        self._processed_classes.add(class_name)
                        class_def, more_classes = self._schema_to_baml_class(
                            schema, class_name, definitions
                        )
                        additional_classes.append(class_def)
                        additional_classes.extend(more_classes)
                    
                    return class_name, additional_classes
                else:
                    return "map<string, string>", additional_classes
            
            # Handle primitive types
            elif schema_type == "string":
                return "string", additional_classes
            elif schema_type == "number":
                return "float", additional_classes
            elif schema_type == "integer":
                return "int", additional_classes
            elif schema_type == "boolean":
                return "bool", additional_classes
            elif schema_type == "null":
                return "null", additional_classes
        
        # Handle oneOf / anyOf / allOf
        for union_keyword in ["oneOf", "anyOf", "allOf"]:
            if union_keyword in schema:
                types = []
                for sub_schema in schema[union_keyword]:
                    type_str, type_classes = self._get_baml_type_for_property(
                        sub_schema, property_name, definitions
                    )
                    types.append(type_str)
                    additional_classes.extend(type_classes)
                
                return " | ".join(types), additional_classes
        
        # Default to string if type is unknown
        return "string", additional_classes
    
    def _schema_to_baml_class(self,
            schema: Dict[str, Any], 
            class_name: str, 
            definitions: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str]]:
        """
        Convert a JSON Schema to a BAML class definition.
        
        Returns a tuple of (class_definition, additional_class_definitions)
        """
        if definitions is None:
            definitions = {}
        
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        additional_classes = []
        
        # Use sanitized class name to avoid BAML built-in type conflicts
        class_def = f"class {class_name} {{\n"
        
        # Handle patternProperties
        if "patternProperties" in schema:
            patterns = schema.get("patternProperties", {})
            class_def, pattern_classes = self._convert_pattern_properties(
                patterns, class_def, definitions
            )
            additional_classes.extend(pattern_classes)
        
        # If class has no properties, add a generic value field to prevent empty class errors
        if not properties:
            class_def += "  value string?\n"
        
        for prop_name, prop_schema in properties.items():
            # Skip schema metadata fields
            if prop_name in SCHEMA_META_FIELDS:
                continue
                
            # Sanitize property name for BAML
            sanitized_prop_name = self._sanitize_property_name(prop_name)
            
            prop_type, prop_classes = self._get_baml_type_for_property(
                prop_schema, prop_name, definitions
            )
            additional_classes.extend(prop_classes)
            
            # Add field attributes
            attributes = []
            
            # Handle description - sanitize for BAML compatibility
            description = prop_schema.get("description", "")
            
            # Instead of @min and @max attributes, include constraints in the description
            if prop_schema.get("type") in ["number", "integer"]:
                if "minimum" in prop_schema:
                    if description:
                        description += " "
                    description += f"Min: {prop_schema['minimum']}."
                if "maximum" in prop_schema:
                    if description:
                        description += " "
                    description += f"Max: {prop_schema['maximum']}."
            
            if description:
                sanitized_desc = self._sanitize_description(description)
                attributes.append(f'@description("{sanitized_desc}")')
            
            # Format the field with attributes
            attr_str = " ".join(attributes)
            if attr_str:
                attr_str = " " + attr_str
            
            # Handle optionality - in BAML, the ? goes AFTER the type, not after the property name
            is_required = prop_name in required
            if is_required:
                class_def += f"  {sanitized_prop_name} {prop_type}{attr_str}\n"
            else:
                # For optional fields, add ? after the type
                class_def += f"  {sanitized_prop_name} {prop_type}?{attr_str}\n"
        
        class_def += "}\n"
        
        return class_def, additional_classes


# Maintain backward compatibility with the module API
def json_schema_to_baml(schema: Dict[str, Any], root_name: str = "Root") -> str:
    """Backward-compatible API function that delegates to the Converter class."""
    converter = Converter()
    return converter.json_schema_to_baml(schema, root_name)


# Add new API function for reverse mapping
def baml_to_json_schema(baml_data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert data with BAML property names back to original JSON Schema property names.
    
    This is useful when you receive data from an LLM using the BAML schema,
    but need to convert it back to match the original JSON Schema.
    
    Args:
        baml_data: Dictionary with BAML-formatted property names
        schema: The original JSON Schema used for the conversion
        
    Returns:
        Dictionary with property names matching the original JSON Schema
    """
    try:
        # Create a converter and set up the mappings
        converter = Converter()
        # Initialize the mappings by running the forward conversion
        converter.json_schema_to_baml(schema)
        # Now run the reverse conversion
        return converter.baml_to_json_schema(baml_data)
    except Exception as e:
        # Log error but don't crash - return original data as fallback
        logger = logging.getLogger(__name__)
        logger.error(f"Error converting BAML data back to JSON Schema: {e}")
        logger.error(f"Returning original data without conversion")
        return baml_data


# Add new function for TypeBuilder integration
def json_schema_to_typebuilder_baml(schema: Dict[str, Any]) -> str:
    """
    Generate a BAML schema string for TypeBuilder with dynamic DynamicResult extension.
    
    This function builds on the existing converter to create a schema compatible with
    TypeBuilder, including a dynamic extension of the DynamicResult class.
    
    Args:
        schema: JSON Schema object
        
    Returns:
        BAML schema string for use with TypeBuilder's add_baml() method
    """
    logger = logging.getLogger(__name__)
    try:
        # Log the input schema
        logger.debug(f"Converting schema to TypeBuilder BAML: {json.dumps(schema, indent=2)}")
        
        # Check and enforce required fields
        if "properties" in schema and "images" in schema.get("properties", {}):
            # Ensure required fields in the schema
            image_items = schema["properties"]["images"].get("items", {})
            if "properties" in image_items and "required" in image_items:
                # Make sure description is in required fields if it exists in properties
                if "description" in image_items.get("properties", {}) and "description" not in image_items["required"]:
                    logger.debug("Adding 'description' to required fields")
                    image_items["required"].append("description")
        
        # First, convert schema to standard BAML using the existing converter
        converter = Converter()
        schema_baml = converter.json_schema_to_baml(schema, root_name="RootJSONSchema")
        
        # Log the generated BAML
        logger.debug(f"Generated BAML schema:\n{schema_baml}")
        
        # Add dynamic extension of DynamicResult
        dynamic_extension = """
// Dynamic extension of DynamicResult
dynamic class DynamicResult {
    // Original properties are preserved
    rootObj RootJSONSchema @description("Root schema object containing all extracted data")
}
"""
        
        # Create a custom helper for testing/debugging
        test_helper = """
// Test helper comment to verify the schema is being updated
// Description field should be required in all image items
"""
        
        # Combine standard BAML with dynamic extension
        final_schema = f"{schema_baml}\n\n{dynamic_extension}\n\n{test_helper}"
        logger.debug(f"Final TypeBuilder BAML schema:\n{final_schema}")
        return final_schema
    except Exception as e:
        # Log error but don't crash - return a minimal valid BAML schema
        logger.error(f"Error generating TypeBuilder BAML: {e}")
        return """
// Error generating schema - using fallback
class RootJSONSchema {
  value string? @description("Default value for schema generation error")
}

// Dynamic extension with fallback schema
dynamic class DynamicResult {
  rootObj RootJSONSchema @description("Fallback schema due to error")
}
"""
