# JSON Schema to BAML Converter

This module provides a utility to convert JSON Schema (draft-07) documents to BAML format for use with the BAML framework.

## Features

- Flat class structure (no nested classes)
- Proper handling of optionality with the `?` syntax
- Union types with `|` syntax
- Support for attributes like `@description`, `@min`, and `@max`
- Reference handling via definitions
- Array type support
- Enum support

## Usage

```python
from src.schema_compiler.converter import Converter

# Load your JSON Schema
import json
with open('your_schema.json', 'r') as f:
    schema = json.load(f)

# Convert to BAML
converter = Converter()
baml_output = converter.json_schema_to_baml(schema, root_name='YourRootClassName')

# Save the BAML output
with open('output.baml', 'w') as f:
    f.write(baml_output)
```

## Example

For a schema like:

```json
{
  "type": "object",
  "title": "Person",
  "properties": {
    "name": {
      "type": "string",
      "description": "The person's full name"
    },
    "age": {
      "type": "integer",
      "minimum": 0,
      "maximum": 120
    },
    "email": {
      "type": "string",
      "format": "email"
    },
    "is_active": {
      "type": "boolean"
    }
  },
  "required": ["name", "age"]
}
```

The converter will generate:

```baml
// Generated from JSON-Schema - DO NOT EDIT BY HAND

class Person {
  name string @description("The person's full name")
  age int @min(0) @max(120)
  email? string
  is_active? bool
}
```

## Limitations

- Only local `$ref` ("#/definitions/…" or "#/$defs/...") pointers are supported
- Complex keywords that BAML cannot express (e.g., `patternProperties`) are included as descriptions to mapped attributes
- External references are not supported

## TODOs

The following features need to be implemented to enhance schema compliance:

1. **External References**: Implement `loader.resolve_refs` to support external references in JSON Schema
   - Support references to external files and URLs
   - Implement proper caching for external schemas
   - Handle circular references across multiple files

2. **Default Values**: Add support for the `default` keyword in JSON Schema [Source](https://docs.boundaryml.com/ref/baml/class#default-values)
   - Preserve default values from the schema
   - Potentially add as a BAML attribute or comment
   - Ensure defaults are properly applied during extraction

3. **Improved Null Handling**: 
   - Ensure proper handling of properties with type: "null"
   - Add more robust support for union types with null

4. **Format Validation**:
   - Add support for format validation (email, date, etc.)
   - Add appropriate BAML annotations for format attributes

5. **Hidden Fields Injection**:
   - Implement automatic injection of the following hidden fields in every object as specified in the architecture:
     - `confidence: float @hidden` - For model self-score (0-100)
     - `unsure?: "not sure"` - Sentinel to avoid hallucinated values
   - These fields help with model confidence tracking and prevent hallucination

## Validation

To validate the generated BAML files, you can use the `baml-cli fmt` command:

```bash
baml-cli fmt --dry-run your_file.baml
```

If the command exits with code 0, the BAML file is valid. 