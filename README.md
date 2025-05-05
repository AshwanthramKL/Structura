# STRUCTURA - Turning Unstructured Docs into Schema-Tight JSON

This repo accompanies the design document for STRUCTURA a system that ingests unstructured documents and emits JSON that passes the desired schema.

* **Language**: Python 3.12  
* **Core libs**: `boundaryml‑baml`, `jsonschema`, `tiktoken`, `google‑ai‑sdk`, `openai-sdk`

## Components

### Schema Compiler

The Schema Compiler converts JSON Schema definitions to BAML types, enabling type-safe LLM outputs. Key features include:

- Converts JSON Schema (draft-07) to BAML class definitions
- Supports flat class structure (no nested classes)
- Handles optionality with BAML's `?` syntax
- Supports union types with `|` syntax
- Adds attributes like `@description`
- Preserves references to definitions
- Properly formats array types

#### Running Tests

To run tests for the schema compiler:

```bash
python run_schema_tests.py
```

The schema compiler tests include:
- Basic conversion tests for simple and complex schemas
- Edge case tests for nested objects, complex arrays, union types, etc.
- Integration tests with BAML CLI tools

## Usage
