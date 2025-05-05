"""
Token-aware planner.

Handles:
* Token counting for schemas and documents
* Chunking decisions based on token thresholds
* Model tier selection
* Task generation for extraction
* Future support for array streaming
"""

from typing import Dict, Any, List, Optional, Union, Tuple

from src.config import MODEL_CONFIG, TOKEN_INPUT_THRESHOLD, TOKEN_OUTPUT_THRESHOLD
from src.utils.token_counter import count_tokens
from src.pipeline.loader.doc_handle import DocHandle

class Planner:
    """
    Token-aware planner that determines extraction strategy based on document size and schema.
    
    Responsibilities:
    - Count tokens for schemas and documents
    - Determine if chunking is needed
    - Select appropriate model tier
    - Generate tasks for extraction 
    - (Future) Support for array streaming
    """
    
    def __init__(self, enable_max_mode: bool = False):
        """
        Initialize the planner.
        
        Args:
            enable_max_mode: Whether to use more powerful (and expensive) models
        """
        self.enable_max_mode = enable_max_mode
    
    def plan(self, doc_handle: DocHandle, schema: Dict[str, Any], schema_baml: str) -> Dict[str, Any]:
        """
        Main planning function that determines extraction strategy, combining 
        chunking decision and model selection in an integrated way.
        
        Args:
            doc_handle: Document handle containing file info
            schema: JSON Schema for extraction
            schema_baml: BAML representation of the schema
            
        Returns:
            Dict containing extraction task details
        """
        # Step 1: Count tokens for schema and document
        schema_tokens = count_tokens(schema_baml)
        doc_tokens = count_tokens(doc_handle)
        
        total_input_tokens = schema_tokens + doc_tokens
        
        # Step 2: Find arrays and analyze them (for future streaming support)
        arrays = self._find_array_paths(schema)
        
        # Step 3: Estimate expected output tokens
        expected_output_tokens = self._estimate_output_tokens(schema, arrays)
        
        # Step 4: Integrated model selection and chunking decision
        selected_model, needs_chunking = self._select_model_and_chunking_strategy(
            total_input_tokens, 
            expected_output_tokens
        )
        
        # Step 5: Analyze arrays for streaming (placeholder for future implementation)
        arrays_for_streaming = self._identify_arrays_for_streaming(arrays, selected_model)
        
        # Step 6: Return comprehensive extraction task
        return {
            "doc_handle": doc_handle,
            "schema": schema,
            "schema_baml": schema_baml,
            "needs_chunking": needs_chunking,
            "model_tier": selected_model,
            "total_input_tokens": total_input_tokens,
            "expected_output_tokens": expected_output_tokens,
            "arrays": arrays,
            "arrays_for_streaming": arrays_for_streaming
        }
    
    def _select_model_and_chunking_strategy(
        self, 
        total_input_tokens: int, 
        expected_output_tokens: int
    ) -> Tuple[str, bool]:
        """
        Integrated approach to select the best model and determine if chunking is needed.
        
        Args:
            total_input_tokens: Total input tokens (schema + document)
            expected_output_tokens: Expected output tokens
            
        Returns:
            Tuple[str, bool]: (selected model tier, needs chunking flag)
        """
        # Select candidate models based on mode
        if self.enable_max_mode:
            candidates = ["full", "pro"]  # Premium models
        else:
            candidates = ["mini", "flash"]  # Standard models
        
        # Try to find a model that can handle without chunking
        for tier in candidates:
            config = MODEL_CONFIG[tier]
            
            # Check if this model can handle the expected output
            if expected_output_tokens <= (TOKEN_OUTPUT_THRESHOLD * config["max_output_tokens"]):
                # Check if this model can handle the input without chunking
                if total_input_tokens <= (TOKEN_INPUT_THRESHOLD * config["context_window"]):
                    return tier, False  # No chunking needed
        
        # If no model can handle without chunking, select based on output capacity
        for tier in candidates:
            config = MODEL_CONFIG[tier]
            if expected_output_tokens <= (TOKEN_OUTPUT_THRESHOLD * config["max_output_tokens"]):
                return tier, True  # Chunking needed
        
        # Default to the model with largest context window if none fits for output
        largest_model = max(candidates, key=lambda t: MODEL_CONFIG[t]["max_output_tokens"])
        return largest_model, True  # Chunking needed
    
    def _estimate_output_tokens(
        self, 
        schema: Dict[str, Any], 
        arrays: List[Tuple[str, Dict[str, Any]]]
    ) -> int:
        """
        Estimate expected output tokens based on schema structure.
        
        Args:
            schema: JSON Schema for extraction
            arrays: List of array paths and their schemas
            
        Returns:
            Dict[str, int]: Expected output tokens
        """
        # Simple array length estimation (fixed for prototype)
        est_len = {path: 10 for path, _ in arrays}  # Assume 10 items per array for now
        
        # Calculate cost per item based on schema leaf structure
        item_cost = {}
        
        for path, leaf_schema in arrays:
            # Simple heuristic based on leaf schema type
            if leaf_schema.get("type") == "string":
                max_length = leaf_schema.get("maxLength", 50)
                # Assume ~4 chars per token
                item_cost[path] = max(1, max_length // 4)
            elif leaf_schema.get("type") in ["number", "integer", "boolean"]:
                # Simple values cost roughly 1 token
                item_cost[path] = 1
            else:
                # Default cost for complex items
                item_cost[path] = 5
        
        # Calculate total expected tokens
        total_output_tokens = sum(item_cost[path] * est_len[path] for path, _ in arrays) + 128
        
        # Return with both keys set to the same value for backward compatibility
        return total_output_tokens
    
    def _find_array_paths(self, schema: Dict[str, Any], path: str = "") -> List[Tuple[str, Dict[str, Any]]]:
        """
        Find all array paths in the schema.
        
        Args:
            schema: JSON Schema object
            path: Current path in the schema
            
        Returns:
            List of tuples containing (path, leaf_schema)
        """
        result = []
        
        # Skip if not an object
        if not isinstance(schema, dict):
            return result
        
        # Check if this is an array
        if schema.get("type") == "array" and "items" in schema:
            result.append((path, schema.get("items", {})))
        
        # Check properties for nested arrays
        if "properties" in schema and isinstance(schema["properties"], dict):
            for prop, prop_schema in schema["properties"].items():
                prop_path = f"{path}.{prop}" if path else prop
                result.extend(self._find_array_paths(prop_schema, prop_path))
        
        # Check additionalProperties for nested arrays
        if "additionalProperties" in schema and isinstance(schema["additionalProperties"], dict):
            result.extend(self._find_array_paths(schema["additionalProperties"], f"{path}.*"))
        
        # Check oneOf/anyOf/allOf for nested arrays
        for key in ["oneOf", "anyOf", "allOf"]:
            if key in schema and isinstance(schema[key], list):
                for i, sub_schema in enumerate(schema[key]):
                    result.extend(self._find_array_paths(sub_schema, f"{path}[{key}_{i}]"))
        
        return result
    
    def _identify_arrays_for_streaming(
        self, 
        arrays: List[Tuple[str, Dict[str, Any]]], 
        model_tier: str
    ) -> List[Dict[str, Any]]:
        """
        Placeholder for future implementation: Identify arrays that need streaming.
        
        In a future implementation, this would analyze arrays to determine which ones
        are too large to extract in a single LLM call and need to be streamed.
        
        Args:
            arrays: List of array paths and their schemas
            model_tier: Selected model tier
            
        Returns:
            List of arrays that need streaming, with metadata
        """
        # Placeholder implementation - returns empty list for now
        # In future implementation, this would return array paths and slice information
        return []
