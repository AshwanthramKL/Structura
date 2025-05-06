"""
BAML Client Generator Utility

This module provides functionality to generate BAML client code at runtime.
It ensures that the generated client is up-to-date with the current BAML schema.
"""

import subprocess
import time
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class BAMLClientGenerator:
    """
    Utility for generating BAML client code at runtime.
    
    This class ensures that the BAML client code is always up-to-date
    with the current BAML schema definitions.
    """
    
    def __init__(
        self,
        src_dir: str = "src/baml_src",
        output_dir: str = "src/baml_client",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the BAML client generator.
        
        Args:
            src_dir: Path to the directory containing BAML source files
            output_dir: Path to output the generated client code
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds
        """
        self.src_dir = Path(src_dir).absolute()
        self.output_dir = Path(output_dir).absolute()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def generate(self, force: bool = False) -> bool:
        """
        Generate the BAML client code.
        
        Args:
            force: Force regeneration even if the client already exists
            
        Returns:
            bool: True if generation was successful, False otherwise
        """
        # Check if generation is needed
        if not force and self._client_exists() and not self._is_outdated():
            logger.info("BAML client is up-to-date, skipping generation")
            return True
            
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to generate with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Generating BAML client (attempt {attempt+1}/{self.max_retries})...")
                
                # Run the BAML CLI generate command
                result = subprocess.run(
                    [
                        "baml-cli", "generate",
                        "--from", str(self.src_dir),
                        "--output", str(self.output_dir)
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                logger.info(f"BAML client generated successfully: {result.stdout.strip()}")
                
                # Wait for files to be fully written
                time.sleep(self.retry_delay)
                
                # Verify generation was successful
                if self._client_exists():
                    logger.info(f"Generated client directory found at: {self.output_dir}")
                    return True
                else:
                    logger.warning("Client directory exists but files may be incomplete")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    
            except subprocess.CalledProcessError as e:
                error_msg = f"Error generating BAML client: {e.stderr}"
                logger.error(error_msg)
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
            except Exception as e:
                error_msg = f"Unexpected error during BAML client generation: {str(e)}"
                logger.error(error_msg)
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        
        return False
    
    def _client_exists(self) -> bool:
        """
        Check if the BAML client files exist.
        
        Returns:
            bool: True if client exists, False otherwise
        """
        client_init = self.output_dir / "__init__.py"
        return client_init.exists()
    
    def _is_outdated(self) -> bool:
        """
        Check if the BAML client is outdated compared to source files.
        
        Returns:
            bool: True if client is outdated, False otherwise
        """
        if not self._client_exists():
            return True
            
        # Get the latest modification time of BAML source files
        latest_src_time = 0
        for file in self.src_dir.glob("*.baml"):
            mod_time = file.stat().st_mtime
            if mod_time > latest_src_time:
                latest_src_time = mod_time
        
        # Get the latest modification time of generated client files
        client_init = self.output_dir / "__init__.py"
        client_time = client_init.stat().st_mtime
        
        # Client is outdated if source files are newer
        return latest_src_time > client_time


# Singleton instance for global use
default_generator = BAMLClientGenerator()

def generate_client(force: bool = False) -> bool:
    """
    Generate the BAML client using the default generator.
    
    Args:
        force: Force regeneration even if the client already exists
        
    Returns:
        bool: True if generation was successful, False otherwise
    """
    return default_generator.generate(force=force)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Generate the client
    success = generate_client(force=True)
    
    if success:
        print("BAML client generated successfully")
    else:
        print("Failed to generate BAML client") 