"""
BAML Client Registry Service

This module provides a service for configuring BAML client registries based on Structura model tiers.
It handles mapping between Structura's model tiers and the corresponding BAML clients,
including fallback mechanisms and retry strategies.
"""

import logging
from typing import Dict, Any, Optional

from baml_py import ClientRegistry, Collector

from src.config import BAML_CLIENT_CONFIG

logger = logging.getLogger(__name__)

class ClientRegistryService:
    """
    Service for configuring BAML client registries based on Structura model tiers.
    
    This service:
    - Maps Structura model tiers to BAML clients
    - Configures fallback mechanisms between model tiers
    - Creates and manages client registries for extraction tasks
    """
    
    def __init__(self):
        """Initialize the client registry service."""
        # Collector for usage metrics
        self.collector = Collector(name="structura-extraction")
        
        # Use the centralized configuration from config.py
        self._tier_mapping = BAML_CLIENT_CONFIG
    
    def get_registry(self, model_tier: str) -> ClientRegistry:
        """
        Get a configured client registry for the specified model tier.
        
        Args:
            model_tier: The model tier to use (mini, flash, full, pro)
            
        Returns:
            ClientRegistry: Configured BAML client registry
            
        Raises:
            ValueError: If the specified model tier is not supported
        """
        # Validate model tier
        if model_tier not in self._tier_mapping:
            supported_tiers = ", ".join(self._tier_mapping.keys())
            raise ValueError(f"Unsupported model tier: {model_tier}. Supported tiers: {supported_tiers}")
            
        # Create a new client registry
        registry = ClientRegistry()
        
        # Configure primary client
        tier_config = self._tier_mapping[model_tier]
        self._add_client(registry, 
                         tier_config["primary"], 
                         tier_config["provider"], 
                         tier_config["options"])
        
        # Configure fallback if available
        if tier_config["fallback"]:
            fallback_tier = tier_config["fallback"].lower().replace("structura", "")
            if fallback_tier in self._tier_mapping:
                fallback_config = self._tier_mapping[fallback_tier]
                
                # Add fallback client
                self._add_client(registry,
                               fallback_config["primary"],
                               fallback_config["provider"],
                               fallback_config["options"])
                
                # Create fallback chain
                registry.add_llm_client(
                    name=f"{tier_config['primary']}WithFallback",
                    provider="fallback",
                    options={
                        "strategy": [tier_config["primary"], fallback_config["primary"]]
                    }
                )
                
                # Set primary to fallback chain
                registry.set_primary(f"{tier_config['primary']}WithFallback")
            else:
                # No fallback tier found, just set primary
                registry.set_primary(tier_config["primary"])
        else:
            # No fallback specified, just set primary
            registry.set_primary(tier_config["primary"])
        
        return registry
    
    def get_collector(self) -> Collector:
        """
        Get the usage metrics collector.
        
        Returns:
            Collector: BAML metrics collector
        """
        return self.collector
    
    def reset_collector(self) -> None:
        """Reset the usage metrics collector."""
        self.collector = Collector(name="structura-extraction")
    
    def _add_client(self, registry: ClientRegistry, name: str, provider: str, options: Dict[str, Any]) -> None:
        """
        Add a client to the registry.
        
        Args:
            registry: The client registry to add to
            name: Client name
            provider: Provider (openai, google-ai, etc.)
            options: Client options
        """
        try:
            registry.add_llm_client(
                name=name,
                provider=provider,
                options=options
            )
            logger.debug(f"Added client {name} with provider {provider}")
        except Exception as e:
            logger.error(f"Failed to add client {name}: {str(e)}")
            # Add a basic client as fallback if the specified one fails
            registry.add_llm_client(
                name=name,
                provider="openai",
                options={
                    "model": "gpt-4.1-mini",
                    "temperature": 0.0,
                    "max_tokens": 32000
                }
            )
            logger.warning(f"Using fallback configuration for client {name}")


# Singleton instance for global use
client_registry_service = ClientRegistryService() 