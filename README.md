# STRUCTURA - Turning Unstructured Docs into Schema-Tight JSON

This repo contains STRUCTURA, a system that ingests unstructured documents and emits JSON that passes the desired schema.

* **Language**: Python 3.12  
* **Core libs**: `boundaryml‑baml`, `jsonschema`, `tiktoken`, `google‑ai‑sdk`, `openai-sdk`, `llama-index`, `typebuilder`

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
- Handles BAML reserved keywords (including Jinja template keywords like `if`, `for`, `with`)

### Document Loader ✅

The Document Loader handles various file types and normalizes them to a common format:

- Handles text files (txt, md)
- Supports PDF loading via Vision APIs
- Extracts content from binary files
- Returns a standardized DocHandle format

### Planner ✅

The Planner module manages token counting and chunking decisions:
- Token counting implementation using Gemini API
- Model tier selection based on token count
- Chunking decision logic based on document size
- Schema analysis for proper extraction planning

### Chunker ✅

The Chunker breaks large documents into manageable pieces:
- Using LlamaIndex SemanticTextSplitter for text documents
- Maintains chunk context for better extraction

### Extractor ✅

The Extractor processes chunks and extracts schema-compliant JSON:
- Full BAML integration for extraction
- TypeBuilder integration for dynamic schema support
- Advanced prompt template design
- Support for both text and image extraction

### Validator ✅

The Validator ensures extracted data conforms to the schema:
- JSON Schema validation
- Detailed error reporting
- Support for complex data structures

## Current Progress

- ✅ Schema Compiler: Fully implemented with TypeBuilder integration
- ✅ Document Loader: Fully implemented with support for various file types
- ✅ Planner: Complete implementation with token-aware planning
- ✅ Chunker: Full implementation with semantic text splitting
- ✅ Extractor: Complete implementation with TypeBuilder integration
- ✅ Validator: Fully implemented for schema conformance checking

## Running the Pipeline

The system includes a generic pipeline script that can process any text with any JSON schema:

```bash
python test_full_pipeline.py --schema <schema_file> --text <text_file> [--output <output_file>]
```

Examples:
```bash
# Basic usage
python test_full_pipeline.py --schema data/schema.json --text data/sample.md

# With output file
python test_full_pipeline.py --schema data/github_actions_schema.json --text "data/github actions sample input.md" --output results.json

# Save logs for detailed analysis
python test_full_pipeline.py --schema data/paper_citations_schema.json --text data/bibtex_file.bib | tee extraction_logs.txt
```

## TypeBuilder Integration

Structura now integrates with TypeBuilder to allow dynamic schema extension at runtime:

- Dynamic generation of BAML schemas from JSON Schema
- Runtime extension of types 
- Support for complex schema validation
- Improved extraction accuracy with structured outputs

## Future Enhancements

Future versions will include:
1. Array streaming for large documents
2. Advanced confidence scoring
3. Complex conflict resolution with human queue
4. Vision-based PDF chunking with structured extraction
5. Advanced evaluation metrics
6. Additional file type support

## Token-Aware Planner

The system includes a token-aware planner that intelligently:
- Counts tokens for schemas and documents using Gemini's API
- Makes chunking decisions based on document size and schema complexity
- Selects appropriate model tiers based on input and output token requirements
- Analyzes arrays in schemas to prepare for future streaming support

