import os
from typing import Dict, Any
from pathlib import Path

def load_env():
    """Load environment variables from .env file if it exists."""
    try:
        # Try to import dotenv
        from dotenv import load_dotenv
        
        # Look for .env file in project root
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"Loaded environment variables from {env_path}")
        else:
            print("No .env file found in project root")
    except ImportError:
        print("python-dotenv not installed. Cannot load .env file.")

# Load environment variables at import time
load_env()

class Settings:
    """Application settings including API keys and configurations."""
    
    def __init__(self):
        # API Keys
        self.google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # Other settings
        self.tokens_per_page_estimate = 500

    @property
    def has_google_api_key(self) -> bool:
        return bool(self.google_api_key)
    
    @property
    def has_openai_api_key(self) -> bool:
        return bool(self.openai_api_key)

# Create a singleton instance
settings = Settings()

LOG_DIR = "runs"

# Model configurations with context windows and token limits
MODEL_CONFIG = {
    "mini": {
        "context_window": 32768, 
        "max_output_tokens": 32768, 
        "family": "openai", 
        "name": "gpt-4.1-mini"
    },
    "flash": {
        "context_window": 65536, 
        "max_output_tokens": 65536, 
        "family": "gemini", 
        "name": "gemini-2.5-flash"
    },
    "full": {
        "context_window": 32768, 
        "max_output_tokens": 32768, 
        "family": "openai", 
        "name": "gpt-4.1"
    },
    "pro": {
        "context_window": 65536, 
        "max_output_tokens": 65536, 
        "family": "gemini", 
        "name": "gemini-2.5-pro"
    }
}

# Token thresholds for chunking and output limits
TOKEN_INPUT_THRESHOLD = 0.85  # Max percentage of context window for input
TOKEN_OUTPUT_THRESHOLD = 0.95  # Max percentage of max_output_tokens

# BAML client configuration mapping 
# Maps Structura model tiers to BAML client configuration
BAML_CLIENT_CONFIG = {
    # Standard tier mapping
    "mini": {
        "primary": "StructuraMini",
        "fallback": "StructuraPro",
        "provider": "openai",
        "options": {
            "model": "gpt-4.1-mini",
            "temperature": 0.0,
            "max_tokens": 32000
        }
    },
    "flash": {
        "primary": "StructuraFlash",
        "fallback": "StructuraPro",
        "provider": "google-ai",
        "options": {
            "model": "gemini-2.5-flash-preview-04-17",
            "temperature": 0.0,
            "max_tokens": 65000
        }
    },
    "full": {
        "primary": "StructuraFull",
        "fallback": "StructuraPro",
        "provider": "openai",
        "options": {
            "model": "gpt-4.1",
            "temperature": 0.0,
            "max_tokens": 32000
        }
    },
    "pro": {
        "primary": "StructuraPro",
        "fallback": "StructuraFull",
        "provider": "google-ai",
        "options": {
            "model": "gemini-2.5-pro-preview-04-17",
            "temperature": 0.0,
            "max_tokens": 65000
        }
    }
}
