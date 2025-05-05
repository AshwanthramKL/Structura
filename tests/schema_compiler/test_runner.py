#!/usr/bin/env python3
"""
Test runner for the schema compiler tests.
"""

import unittest
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

if __name__ == "__main__":
    # Discover and run tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(
        start_dir=str(Path(__file__).parent),
        pattern="test_*.py"
    )
    
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Exit with non-zero code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1) 