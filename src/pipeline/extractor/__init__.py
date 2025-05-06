"""
Extractor module for converting text or images into structured data.

This module implements schema-driven extraction from unstructured content
(text documents and images/PDFs) into structured JSON using BAML-powered LLMs.
"""

from src.pipeline.extractor.extractor import Extractor, ExtractionResult

__all__ = ["Extractor", "ExtractionResult"] 