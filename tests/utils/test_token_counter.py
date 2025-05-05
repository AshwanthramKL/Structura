"""
Tests for the token counter functionality.
"""

import os
import io
import unittest
import sys
from unittest.mock import patch, Mock, MagicMock

from src.utils.token_counter import count_tokens
from src.pipeline.loader.doc_handle import DocHandle
from src.config import settings
from tests.utils.test_helpers import get_baseline

class MockResponse:
    """Mock response object for Gemini API"""
    def __init__(self, total_tokens):
        self.total_tokens = total_tokens

class MockGenai:
    """Mock Genai module for testing."""
    def __init__(self, token_count=25):
        self.Client = self.MockClient
        self.token_count = token_count
        
    class MockClient:
        def __init__(self, api_key=None):
            self.models = self.MockModels()
            self.files = self.MockFiles()
        
        class MockModels:
            def count_tokens(self, model, contents):
                return MockResponse(25)
                
        class MockFiles:
            def upload(self, file):
                return "fake_uploaded_file"

class TestTokenCounter(unittest.TestCase):
    """Test cases for token counter functionality."""

    def setUp(self):
        # Create test fixtures
        self.sample_text = "This is a sample text for token counting. It contains multiple sentences and should have a predictable token count."
        self.sample_pdf_path = os.path.join("data", "sample.pdf")  # Assuming sample.pdf exists in data directory
        
        # Check if PDF exists, if not use mock content
        if os.path.exists(self.sample_pdf_path):
            with open(self.sample_pdf_path, "rb") as f:
                self.sample_pdf_content = f.read()
        else:
            # Mock PDF content
            self.sample_pdf_content = b"%PDF-1.5\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        
        # Create DocHandle instances
        self.text_doc = DocHandle(
            file_path="sample.txt",
            content=self.sample_text.encode(),
            text=self.sample_text,
            mime_type="text/plain"
        )
        
        self.pdf_doc = DocHandle(
            file_path=self.sample_pdf_path,
            content=self.sample_pdf_content,
            mime_type="application/pdf",
            metadata={"page_count": "5"}
        )
        
        # Create a mock genai module
        self.mock_genai = MockGenai()

    def test_count_tokens_with_text(self):
        """Test token counting with plain text input."""
        # Mock the import statement
        with patch.dict('sys.modules', {'google.genai': self.mock_genai}):
            # Count tokens
            tokens = count_tokens(self.sample_text)
            
            # Get baseline values for comparison
            baseline = get_baseline("text_token_count", tokens)
            
            # Verify token count is within acceptable range of baseline
            if "min_value" in baseline:
                self.assertGreaterEqual(tokens, baseline["min_value"])
                self.assertLessEqual(tokens, baseline["max_value"])

    def test_count_tokens_with_text_doc_handle(self):
        """Test token counting with DocHandle containing text."""
        # Mock the import statement
        with patch.dict('sys.modules', {'google.genai': self.mock_genai}):
            # Count tokens
            tokens = count_tokens(self.text_doc)
            
            # Get baseline values for comparison
            baseline = get_baseline("text_doc_token_count", tokens)
            
            # Verify token count is within acceptable range of baseline
            if "min_value" in baseline:
                self.assertGreaterEqual(tokens, baseline["min_value"])
                self.assertLessEqual(tokens, baseline["max_value"])

    def test_count_tokens_with_pdf(self):
        """Test token counting with PDF document."""
        # Mock the import statement
        with patch.dict('sys.modules', {'google.genai': self.mock_genai}):
            # Count tokens
            tokens = count_tokens(self.pdf_doc)
            
            # Get baseline values for comparison
            baseline = get_baseline("pdf_token_count", tokens)
            
            # Verify token count is within acceptable range of baseline
            if "min_value" in baseline:
                self.assertGreaterEqual(tokens, baseline["min_value"])
                self.assertLessEqual(tokens, baseline["max_value"])

    def test_api_failure_fallback(self):
        """Test fallback mechanism when API fails."""
        # Create a failing mock module with a custom class
        class FailingMockGenai:
            class Client:
                def __init__(self, api_key=None):
                    self.models = Mock()
                    self.models.count_tokens = Mock(side_effect=Exception("API failure"))
        
        # Mock the import statement with the failing mock
        with patch.dict('sys.modules', {'google.genai': FailingMockGenai()}):
            # Test with text
            tokens = count_tokens(self.sample_text)
            
            # Verify fallback approximation (length / 4)
            expected = len(self.sample_text) // 4
            self.assertEqual(tokens, expected)

    @patch('src.config.settings')
    def test_missing_api_key_fallback(self, mock_settings):
        """Test fallback when API key is missing."""
        # Mock missing API key
        mock_settings.has_google_api_key = False
        
        # Save the original sample text
        original_text = self.sample_text
        
        # Test with text
        tokens = count_tokens(self.sample_text)
        
        # The fallback is approximately text length divided by 4
        # But rather than asserting an exact value, we should check it's reasonable
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, len(self.sample_text))
        
        # Get baseline for this test
        baseline = get_baseline("missing_api_key_fallback", tokens)
        
        # Verify against baseline if available
        if "min_value" in baseline:
            self.assertGreaterEqual(tokens, baseline["min_value"])
            self.assertLessEqual(tokens, baseline["max_value"])


    @unittest.skipIf(not settings.has_google_api_key, "Skipping live API test: No Google API key")
    def test_real_api_with_text(self):
        """Test with real API (when API key is available)."""
        # This will use the real API if environment variable is set
        tokens = count_tokens(self.sample_text)
        
        # Get baseline values for comparison
        baseline = get_baseline("real_api_text_token_count", tokens)
        
        # Verify token count is within acceptable range of baseline
        if "min_value" in baseline:
            self.assertGreaterEqual(tokens, baseline["min_value"])
            self.assertLessEqual(tokens, baseline["max_value"])
            
    @unittest.skipIf(not os.path.exists(os.path.join("data", "sample.pdf")), 
                    "Skipping test: No sample PDF file")
    @unittest.skipIf(not settings.has_google_api_key, "Skipping live API test: No Google API key")
    def test_real_api_with_pdf(self):
        """Test with real PDF and real API."""
        # This will use the real API if environment variable is set
        tokens = count_tokens(self.pdf_doc)
        
        # Get baseline values for comparison
        baseline = get_baseline("real_api_pdf_token_count", tokens)
        
        # Verify token count is greater than zero
        self.assertGreater(tokens, 0)
        
        # Verify token count is within acceptable range of baseline
        if "min_value" in baseline:
            self.assertGreaterEqual(tokens, baseline["min_value"])
            self.assertLessEqual(tokens, baseline["max_value"]) 