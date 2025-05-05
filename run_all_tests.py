#!/usr/bin/env python3
"""
Master script to run all tests for Structura.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_subprocess(command, description):
    """Run a subprocess command and return the result."""
    print(f"\n{'='*80}")
    print(f"Running {description}...")
    print(f"{'-'*80}\n")
    
    try:
        result = subprocess.run(
            command,
            capture_output=False,
            text=True,
            check=False
        )
        success = result.returncode == 0
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{status}: {description}")
        return success
    except Exception as e:
        print(f"\n❌ ERROR: {description} - {str(e)}")
        return False

def main():
    # Track results
    results = {}
    
    # Run schema compiler tests
    results["Schema Compiler Tests"] = run_subprocess(
        [sys.executable, "run_schema_tests.py"],
        "Schema Compiler Tests"
    )
    
    # Run unit tests
    results["Unit Tests"] = run_subprocess(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        "Unit Tests"
    )
    
    # Print summary
    print("\n\n" + "="*40)
    print("Structura Test Summary")
    print("="*40)
    
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")
    
    print("-"*40)
    print(f"Overall Result: {success_count}/{total_count} test suites passed")
    print("="*40)
    
    # Return success if all tests passed
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 