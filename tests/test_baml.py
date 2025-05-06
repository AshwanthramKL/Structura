"""
Tests for BAML integration.

These tests verify that the core components of our BAML integration
are working properly:
1. Client generator
2. Client registry service
"""

import unittest
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BAMLIntegrationTests(unittest.TestCase):
    """Test cases for BAML integration."""
    
    def test_client_generator(self):
        """Test the BAML client generator."""
        logger.info("Testing BAML client generator...")
        
        from src.baml_utils import generate_client
        
        # Test generating the client
        success = generate_client(force=True)
        
        self.assertTrue(success, "Client generation should succeed")
        
        client_dir = Path("src/baml_client")
        self.assertTrue(client_dir.exists() and (client_dir / "__init__.py").exists(),
                        f"Client directory should exist at {client_dir.absolute()}")
        
        logger.info("Client generation test passed!")
    
    def test_client_registry(self):
        """Test the client registry service."""
        logger.info("Testing client registry service...")
        
        from src.baml_utils import client_registry_service
        
        # Test registry for each tier
        for tier in ["mini", "flash", "full", "pro"]:
            logger.info(f"Testing {tier} tier registry...")
            registry = client_registry_service.get_registry(tier)
            
            # Check if registry has a primary client (safely, without using internal attributes)
            self.assertIsNotNone(registry, f"Registry for {tier} tier should not be None")
            
            # Test that we can add a client (which implies the registry is functional)
            try:
                registry.add_llm_client(
                    name="TestClient",
                    provider="openai",
                    options={"model": "gpt-3.5-turbo"}
                )
                logger.info(f"Successfully added test client to {tier} tier registry")
            except Exception as e:
                self.fail(f"Failed to add test client to {tier} tier registry: {e}")
        
        # Test collector
        collector = client_registry_service.get_collector()
        self.assertIsNotNone(collector, "Collector should not be None")
        
        logger.info("Client registry test passed!")


if __name__ == "__main__":
    unittest.main() 