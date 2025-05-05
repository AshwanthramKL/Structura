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
- Complex keywords that BAML cannot express (e.g., `patternProperties`) are included as comments
- External references are not supported

## Validation

To validate the generated BAML files, you can use the `baml-cli fmt` command:

```bash
baml-cli fmt --dry-run your_file.baml
```

If the command exits with code 0, the BAML file is valid. 