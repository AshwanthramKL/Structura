#!/usr/bin/env python3
"""
Generic pipeline for Structura extraction with TypeBuilder.

This script provides a generic pipeline that can extract structured data from any text 
content using any JSON schema. The steps include:

1. Loading a document and schema from files
2. Chunking the document using TextChunker
3. Planning extraction with token-aware Planner
4. Extracting structured data with TypeBuilder
5. Displaying and validating the results

Usage:
    python test_full_pipeline.py --schema <schema_file> --text <text_file> [--output <output_file>]

Examples:
    # Basic usage
    python test_full_pipeline.py --schema data/schema.json --text data/sample.md

    # With output file
    python test_full_pipeline.py --schema data/github_actions_schema.json --text "data/github actions sample input.md" --output results.json
    
    # Using paths with spaces
    python test_full_pipeline.py --schema "/path/with spaces/schema.json" --text "/path/with spaces/text.md"

    # Real example with GitHub Actions schema
    python test_full_pipeline.py --schema "data/github_actions_schema.json" --text "data/github actions sample input.md"

Notes:
    - The schema file must be a valid JSON Schema document
    - Text files can be any format (.txt, .md, .html) - the script will detect the format based on file extension
    - If validation errors occur, check that your schema matches the expected format of your text content
    - For paths with spaces, use quotes around the path
"""

import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Union

from src.pipeline.chunker.text_chunker import TextChunker
from src.pipeline.extractor import Extractor
from src.pipeline.loader.doc_handle import DocHandle
from src.pipeline.planner.planner import Planner
from src.schema_compiler.validator import SchemaValidator
from src.schema_compiler.converter import json_schema_to_baml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_full_pipeline(schema_file: str, text_file: str, output_file: Optional[str] = None) -> Union[Dict[str, Any], None]:
    """
    Run the complete Structura extraction pipeline on the provided files.
    
    Args:
        schema_file: Path to JSON schema file
        text_file: Path to text content file
        output_file: Optional path to save output JSON
        
    Returns:
        The extracted structured data or None if processing fails
    """
    logger.info(f"Starting pipeline with schema: {schema_file} and text: {text_file}")
    
    # Step 1: Load the schema
    logger.info("Loading schema...")
    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_json = json.load(f)
        logger.info(f"Schema loaded with {len(json.dumps(schema_json))} characters")
    except Exception as e:
        logger.error(f"Failed to load schema: {e}")
        return None
    
    # Step 2: Load the text content
    logger.info("Loading text content...")
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            text_content = f.read()
        logger.info(f"Text content loaded with {len(text_content)} characters")
    except Exception as e:
        logger.error(f"Failed to load text content: {e}")
        return None
    
    # Step 3: Create DocHandle
    text_bytes = text_content.encode('utf-8')
    # Determine mime type based on file extension
    mime_type = "text/plain"
    if text_file.lower().endswith(('.md', '.markdown')):
        mime_type = "text/markdown"
    elif text_file.lower().endswith('.html'):
        mime_type = "text/html"
    
    doc_handle = DocHandle(
        file_path=text_file,
        content=text_bytes,
        mime_type=mime_type,
        text=text_content,
        metadata={"source": text_file}
    )
    
    # Step 4: Chunk the document using TextChunker
    logger.info("Chunking document...")
    chunker = TextChunker()
    chunks = chunker.chunk(doc_handle)
    logger.info(f"Document chunked into {len(chunks)} chunks")
    
    # Step 5: Create extraction plan using Planner
    logger.info("Creating extraction plan...")
    planner = Planner()
    
    # Convert JSON schema to BAML using schema compiler
    logger.info("Converting JSON schema to BAML...")
    schema_baml = json_schema_to_baml(schema_json, root_name="Root")
    logger.info(f"BAML schema generated with {len(schema_baml.splitlines())} lines")
    
    # Create extraction plan
    plan = planner.plan(
        doc_handle=doc_handle,
        schema_json=schema_json,
        schema_baml=schema_baml
    )
    logger.info(f"Extraction plan created with model tier: {plan.model_tier}")
    logger.info(f"Total input tokens: {plan.total_input_tokens}, Expected output tokens: {plan.expected_output_tokens}")
    logger.info(f"Chunking needed: {plan.needs_chunking}")
    
    # Step 6: Perform extraction using Extractor with TypeBuilder
    logger.info("Extracting structured data...")
    extractor = Extractor()
    result = extractor.extract(chunks, plan)
    
    # Step 7: Validate results against schema
    logger.info("Validating extraction results...")
    is_valid, errors = SchemaValidator.validate(result, schema_json, raise_exception=False)
    
    if is_valid:
        logger.info("Validation successful: Result conforms to schema")
    else:
        logger.warning(f"Validation failed: {len(errors)} errors found")
        for error in errors[:3]:  # Show first few errors
            logger.warning(f"Error at {error['path']}: {error['message']}")
    
    # Step 8: Output results
    logger.info("Extraction complete!")
    print("\n" + "="*80)
    print("EXTRACTED STRUCTURED DATA:")
    print("="*80)
    print(json.dumps(result, indent=2))
    print("="*80 + "\n")
    
    # Save to file if requested
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Results saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    return result

def main():
    """Parse command line arguments and run the pipeline."""
    parser = argparse.ArgumentParser(description="Run Structura extraction pipeline")
    parser.add_argument('--schema', required=True, help='Path to JSON schema file')
    parser.add_argument('--text', required=True, help='Path to text content file')
    parser.add_argument('--output', help='Optional path to save output JSON')
    
    args = parser.parse_args()
    
    run_full_pipeline(args.schema, args.text, args.output)

if __name__ == "__main__":
    main() 