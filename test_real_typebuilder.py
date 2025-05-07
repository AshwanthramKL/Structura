#!/usr/bin/env python3
"""
Real-world test for TypeBuilder integration with Structura's extractor.

This script makes actual API calls to test that our TypeBuilder integration works correctly.
"""

import json
import logging
from pathlib import Path

from src.pipeline.extractor import Extractor
from src.pipeline.planner.planner import ExtractionPlan
from src.pipeline.chunker.text_chunker import Chunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_test():
    """Run a real-world test of TypeBuilder integration."""
    logger.info("Starting TypeBuilder integration test with real API calls")
    
    # Create a schema for a person with contact information
    schema_json = {
        "type": "object",
        "properties": {
            "person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The person's full name"},
                    "age": {"type": "integer", "description": "The person's age in years"},
                    "occupation": {"type": "string", "description": "The person's job title"},
                    "contact": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "Email address"},
                            "phone": {"type": "string", "description": "Phone number"}
                        }
                    }
                },
                "required": ["name"]
            },
            "company": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Company name"},
                    "industry": {"type": "string", "description": "Industry sector"}
                }
            }
        },
        "required": ["person"]
    }
    
    # Define BAML schema
    schema_baml = """
    class Person {
        name string @description("The person's full name")
        age int? @description("The person's age in years")
        occupation string? @description("The person's job title")
        contact Contact? @description("Contact information")
    }

    class Contact {
        email string? @description("Email address")
        phone string? @description("Phone number")
    }

    class Company {
        name string @description("Company name")
        industry string? @description("Industry sector")
    }
    """
    
    # Create a sample text
    sample_text = """
    John Smith is a 35-year-old software engineer at Acme Technologies.
    He specializes in cloud infrastructure and has worked at the company for 5 years.
    You can reach him at john.smith@acmetech.com or by phone at (555) 123-4567.
    Acme Technologies is a leader in the information technology sector.
    """
    
    # Create a chunk with the sample text
    chunk = Chunk(
        text=sample_text,
        metadata={"source": "test"},
        index=0,
        total_chunks=1
    )
    
    # Create an extraction plan
    plan = ExtractionPlan(
        doc_handle=None,  # Not needed for this test
        schema_json=schema_json,
        schema_baml=schema_baml,
        model_tier="pro", # Use mini to reduce costs
        needs_chunking=False,
        total_input_tokens=0,
        expected_output_tokens=0
    )
    
    # Create an extractor
    extractor = Extractor()
    
    # Run the extraction
    logger.info("Running extraction with TypeBuilder...")
    result = extractor.extract([chunk], plan)
    
    # Print the result
    logger.info("Extraction result:")
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    run_test() 