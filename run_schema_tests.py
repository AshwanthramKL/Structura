#!/usr/bin/env python3
"""
Runner script for the schema compiler tests.
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run the schema compiler tests."""
    test_runner = Path("tests") / "schema_compiler" / "test_runner.py"
    
    if not test_runner.exists():
        print(f"❌ Test runner not found at {test_runner}")
        return False
    
    print("Running schema compiler tests...")
    result = subprocess.run(
        [sys.executable, str(test_runner)],
        check=False
    )
    
    return result.returncode == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 