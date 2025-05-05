# STRUCTURA - Turning Unstructured Docs into Schema-Tight JSON

This repo accompanies the design document for STRUCTURA a system that ingests unstructured documents and emits JSON that passes the desired schema.

* **Language**: Python 3.12  
* **Core libs**: `boundaryml‑baml`, `jsonschema`, `tiktoken`, `google‑ai‑sdk`, `openai-sdk`, `llama-index`

## Components

### Schema Compiler ✅

The Schema Compiler converts JSON Schema definitions to BAML types, enabling type-safe LLM outputs. Key features include:

- Converts JSON Schema (draft-07) to BAML class definitions
- Supports flat class structure (no nested classes)
- Handles optionality with BAML's `?` syntax
- Supports union types with `|` syntax
- Adds attributes like `@description`
- Preserves references to definitions
- Properly formats array types

### Document Loader ✅

The Document Loader handles various file types and normalizes them to a common format:

- Handles text files (txt, md)
- Supports PDF loading via Vision APIs
- Extracts content from binary files
- Returns a standardized DocHandle format

### Planner 🔄

The Planner module manages token counting and chunking decisions:
- Basic token counting implementation
- Model tier selection based on token count
- Simple chunking decision logic
- Note: Advanced array handling deferred for future versions

### Chunker 🔄

The Chunker breaks large documents into manageable pieces:
- Using LlamaIndex SemanticTextSplitter for text documents
- Simple approach without custom LLM integration
- Note: Advanced PDF chunking deferred for future versions

### Extractor 🔄

The Extractor processes chunks and extracts schema-compliant JSON:
- Basic BAML integration for extraction
- Simple prompt template design
- Note: Streaming and confidence scoring deferred for future versions

### Merger 🔄

The Merger combines extracted chunks into a final document:
- Basic first-write-wins approach for scalars
- Simple array concatenation
- Basic conflict detection
- Note: Complex conflict resolution deferred for future versions

## Current Progress

- ✅ Schema Compiler: Fully implemented with tests
- ✅ Document Loader: Fully implemented with tests for various file types
- 🔄 Planner: Simplified implementation in progress
- 🔄 Chunker: Simplified implementation in progress
- 🔄 Extractor: Simplified implementation in progress
- 🔄 Merger: Simplified implementation in progress

## Prototype Scope

For the initial prototype, we are implementing a simplified version that demonstrates core functionality:

1. Basic document processing pipeline
2. Text-based chunking using LlamaIndex
3. BAML integration for schema-compliant extraction
4. Simple merging approach

See `.cursor/deferred_features.md` for details on features deferred to future versions.

## Running Tests

```bash
python run_schema_tests.py  # Schema compiler tests
python run_tests.py         # General tests
```

## Demo

To run a simple end-to-end demo:
```bash
# Coming soon
```

## Future Enhancements

Future versions will include:
1. Array streaming for large documents
2. Advanced confidence scoring
3. Complex conflict resolution with human queue
4. Vision-based PDF chunking
5. Advanced evaluation metrics
6. Additional file type support


The schema compiler tests include:
- Basic conversion tests for simple and complex schemas
- Edge case tests for nested objects, complex arrays, union types, etc.
- Integration tests with BAML CLI tools

## Token-Aware Planner

The system includes a token-aware planner that intelligently:
- Counts tokens for schemas and documents using Gemini's API
- Makes chunking decisions based on document size and schema complexity
- Selects appropriate model tiers based on input and output token requirements
- Analyzes arrays in schemas to prepare for future streaming support

