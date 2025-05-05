"""
Helper utilities for tests, including baseline value management.
"""

import os
import json
from typing import Dict, Any, Optional

BASELINE_FILE = os.path.join(os.path.dirname(__file__), "baseline_values.json")

def load_baseline_values() -> Dict[str, Any]:
    """
    Load saved baseline values from file.
    
    Returns:
        Dict containing baseline values for different test cases
    """
    if not os.path.exists(BASELINE_FILE):
        return {}
    
    try:
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load baseline values: {e}")
        return {}

def save_baseline_values(values: Dict[str, Any]) -> None:
    """
    Save baseline values to file.
    
    Args:
        values: Dict containing baseline values to save
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(BASELINE_FILE), exist_ok=True)
    
    try:
        # If file exists, merge with existing values
        existing = load_baseline_values() if os.path.exists(BASELINE_FILE) else {}
        existing.update(values)
        
        with open(BASELINE_FILE, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        print(f"Error saving baseline values: {e}")

def get_baseline(key: str, actual_value: Optional[Any] = None, tolerance: int = 100) -> Dict[str, Any]:
    """
    Get baseline value for a test case. If running in "dry run" mode or baseline doesn't
    exist, the actual value is saved as baseline.
    
    Args:
        key: Unique identifier for the test case
        actual_value: The actual value from the current run (to save in dry run mode)
        tolerance: Tolerance range for numeric values (+/- this amount)
        
    Returns:
        Dict with baseline, min_value, max_value (for numeric baselines with tolerance)
    """
    baselines = load_baseline_values()
    
    # Check if we're in dry run mode (set by environment variable)
    is_dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    
    # If in dry run mode or baseline doesn't exist, save the actual value
    if is_dry_run or key not in baselines:
        if actual_value is not None:
            save_baseline_values({key: actual_value})
            baselines[key] = actual_value
    
    baseline = baselines.get(key)
    
    # For numeric values, include tolerance range
    if isinstance(baseline, (int, float)):
        return {
            "baseline": baseline,
            "min_value": baseline - tolerance,
            "max_value": baseline + tolerance
        }
    
    return {"baseline": baseline} 