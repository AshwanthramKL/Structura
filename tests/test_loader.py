import unittest
import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.loader.file_loader import FileLoader, DocHandle

class TestFileLoader(unittest.TestCase):
    """Tests for the FileLoader component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.md_file = self.data_dir / "github actions sample input.md"
        self.json_file = self.data_dir / "github_actions_schema.json"
        self.bib_file = self.data_dir / "NIPS-2017-attention-is-all-you-need-Bibtex.bib"
        self.pdf_files = list(self.data_dir.glob("*.pdf"))
        
        # Ensure test files exist
        self.assertTrue(self.md_file.exists(), f"Test file not found: {self.md_file}")
        self.assertTrue(self.json_file.exists(), f"Test file not found: {self.json_file}")
        self.assertTrue(self.bib_file.exists(), f"Test file not found: {self.bib_file}")
        
        # Initialize FileLoader
        FileLoader.initialize()
    
    def test_load_markdown_file(self):
        """Test loading a markdown file."""
        doc_handle = FileLoader.load_file(str(self.md_file))
        
        self.assertIsInstance(doc_handle, DocHandle)
        self.assertEqual(doc_handle.file_path, str(self.md_file))
        self.assertEqual(doc_handle.mime_type, "text/markdown")
        self.assertGreater(doc_handle.size, 0)
        self.assertIsNotNone(doc_handle.text)
        self.assertIn("MkDocs Publisher", doc_handle.text)
        self.assertEqual(doc_handle.metadata["extension"], ".md")
    
    def test_load_json_file(self):
        """Test loading a JSON file."""
        doc_handle = FileLoader.load_file(str(self.json_file))
        
        self.assertIsInstance(doc_handle, DocHandle)
        self.assertEqual(doc_handle.file_path, str(self.json_file))
        self.assertEqual(doc_handle.mime_type, "application/json")
        self.assertGreater(doc_handle.size, 0)
        
        # Test JSON decoding from the loaded file
        text_content = FileLoader.get_text_content(doc_handle)
        json_data = json.loads(text_content)
        self.assertIsInstance(json_data, dict)
        self.assertIn("$schema", json_data)
    
    def test_load_bibtex_file(self):
        """Test loading a BibTeX file."""
        doc_handle = FileLoader.load_file(str(self.bib_file))
        
        self.assertIsInstance(doc_handle, DocHandle)
        self.assertEqual(doc_handle.file_path, str(self.bib_file))
        self.assertIn(doc_handle.mime_type, ["application/x-bibtex", "text/plain"])
        self.assertGreater(doc_handle.size, 0)
        self.assertIsNotNone(doc_handle.text)
        self.assertIn("@inproceedings", doc_handle.text)
        self.assertEqual(doc_handle.metadata["extension"], ".bib")
    
    def test_pdf_loading(self):
        """Test loading PDF files and extracting metadata."""
        # Skip test if no PDF files are found
        if len(self.pdf_files) == 0:
            self.skipTest("No PDF files found in data directory for testing")
        
        # Test the first PDF file found
        pdf_file = self.pdf_files[0]
        
        doc_handle = FileLoader.load_file(str(pdf_file))
        
        # Basic checks
        self.assertIsInstance(doc_handle, DocHandle)
        self.assertEqual(doc_handle.file_path, str(pdf_file))
        self.assertEqual(doc_handle.mime_type, "application/pdf")
        self.assertGreater(doc_handle.size, 0)
        
        # PDF text should be None as we don't extract it directly
        self.assertIsNone(doc_handle.text)
        
        # Verify metadata
        self.assertEqual(doc_handle.metadata["extension"], ".pdf")
        self.assertEqual(doc_handle.metadata["filename"], pdf_file.name)
        
        # Page count may be available if PDF libraries are installed
        if "page_count" in doc_handle.metadata:
            self.assertGreater(doc_handle.metadata["page_count"], 0)
    
    def test_get_text_content(self):
        """Test extracting text content from different file types."""
        # Test with markdown file that has text
        md_handle = FileLoader.load_file(str(self.md_file))
        md_text = FileLoader.get_text_content(md_handle)
        self.assertIsNotNone(md_text)
        self.assertIn("MkDocs Publisher", md_text)
        
        # Test with JSON file
        json_handle = FileLoader.load_file(str(self.json_file))
        json_text = FileLoader.get_text_content(json_handle)
        self.assertIsNotNone(json_text)
        self.assertIn("$schema", json_text)
        
        # PDF should raise NotImplementedError when trying to get text content
        if len(self.pdf_files) > 0:
            pdf_handle = FileLoader.load_file(str(self.pdf_files[0]))
            with self.assertRaises(NotImplementedError):
                FileLoader.get_text_content(pdf_handle)


if __name__ == "__main__":
    unittest.main() 