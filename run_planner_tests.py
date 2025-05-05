#!/usr/bin/env python
"""
Run tests for the token-aware planner and token counter.

Usage:
    python run_planner_tests.py              # Run tests normally
    DRY_RUN=1 python run_planner_tests.py    # Run in dry run mode to establish baselines
    
Set GOOGLE_API_KEY environment variable or add it to .env file for full test coverage.
"""

import os
import sys
import unittest
import argparse
from src.config import load_env

def main():
    """Run token-aware planner tests."""
    # Explicitly load environment variables
    load_env()
    
    parser = argparse.ArgumentParser(description="Run token-aware planner tests")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Run in dry run mode to establish baseline values")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Run with verbose output")
    
    args = parser.parse_args()
    
    # Set dry run environment variable if requested
    if args.dry_run:
        os.environ["DRY_RUN"] = "1"
        print("Running in DRY RUN mode - establishing baseline values")
    
    # Check for API key
    if not os.environ.get("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY environment variable is not set.")
        print("Some tests will be skipped or use fallback approximations.")
        print("Add GOOGLE_API_KEY to your environment or .env file for full test coverage.")
    
    # Discover and run tests
    test_loader = unittest.TestLoader()
    
    # Specify test directories
    test_dirs = [
        os.path.join("tests", "utils"),
        os.path.join("tests", "pipeline")
    ]
    
    # Load tests from specified directories
    test_suite = unittest.TestSuite()
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            tests = test_loader.discover(test_dir, pattern="test_*.py")
            test_suite.addTests(tests)
    
    # Run tests
    verbosity = 2 if args.verbose else 1
    test_runner = unittest.TextTestRunner(verbosity=verbosity)
    result = test_runner.run(test_suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main()) 