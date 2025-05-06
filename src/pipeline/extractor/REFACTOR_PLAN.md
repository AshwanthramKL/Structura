# Extractor Component Refactoring Plan

## Current Implementation Analysis

After reviewing the extractor implementation and comparing it with BAML best practices, we've identified several issues that need to be addressed.

### Critical Issues

1. ✅ **Project Structure Problems**
   - BAML source files (`baml_src`) are in the project root, not within the `src` package
   - Generated BAML client (`baml_client`) is in the project root, causing import issues 
   - Import statements like `from baml_client import b` break when run from within `src` package

2. ✅ **No Runtime Client Generation**
   - The current implementation doesn't regenerate the BAML client at runtime
   - This creates a risk of using outdated client code if BAML schemas change
   - No failsafe if client generation fails or client is missing

3. ✅ **Unsafe Dynamic Function Access**
   - Using `getattr(b, "extractor")` is error-prone
   - No type checking or verification that the function exists
   - No clear error handling if function name changes

4. ✅ **ClientRegistry Implementation Mismatch**
   - Manual registry creation in the extractor doesn't match client definitions in `clients.baml`
   - No leveraging of predefined clients in BAML files
   - Inconsistent model parameters across config and BAML definitions

5. ✅ **Absent Fallback Mechanisms**
   - No proper fallback strategies between models
   - Missing retry logic with exponential backoff
   - No handling of timeouts or other API failures

### Secondary Issues

6. ✅ **Model Tier Inconsistency**
   - Model tiers in `config.py` (mini, flash, full, pro) don't align with client definitions
   - No mapping between application tiers and BAML clients

7. ✅ **Missing Metrics Collection**
   - No usage tracking or token consumption metrics
   - Can't measure performance or cost of extraction operations

8. ⬜ **No Streaming Support**
   - Implementation doesn't use BAML's streaming capabilities for large responses
   - Potential timeouts with large documents

9. ✅ **Manual JSON Validation**
   - Performs manual validation rather than using BAML's built-in validation
   - Duplicate validation logic that could become inconsistent

10. ✅ **Inefficient Error Handling**
    - Current retry mechanism is basic and doesn't handle different error types differently
    - No logging of specific error causes for debugging

## Implemented Solution

We've refactored the extractor component with the following improvements:

### 1. ✅ Reorganized Project Structure
```
src/
  ├── baml_src/       # BAML definition files
  ├── baml_client/    # Generated client (via runtime generation)
  ├── baml_utils/     # BAML utilities (client generation, registry service)
  ├── pipeline/
  │   ├── extractor/  # Updated extractor implementation
  │   └── ...
  └── ...
```

This structure is consistent with BAML naming conventions and keeps related components organized.

### 2. ✅ Runtime Client Generation
- Implemented `BAMLClientGenerator` in `src/baml_utils/client_generator.py`
- Added verification of successful generation
- Implemented file modification timestamp checking
- Added retry mechanisms with proper error handling

### 3. ✅ Client Registry Service
- Implemented `ClientRegistryService` in `src/baml_utils/client_registry_service.py`
- Created mapping between Structura model tiers and BAML clients
- Added proper fallback chains between tiers
- Implemented collector for usage metrics

### 4. ✅ Redesigned Extractor Class
- Completely rewrote the implementation in `src/pipeline/extractor/extractor.py`
- Uses dynamic imports to avoid linter errors
- Added structured result handling with `ExtractionResult` class
- Implemented more robust error handling
- Added token usage tracking with defensive attribute access
- Maintained backward compatibility with the pipeline

### 5. ✅ Interface Improvements
- Modified `extract()` method to consistently return dictionaries
- Added success/failure flags in `ExtractionResult`
- Added token usage reporting
- Improved error messages with specific error reporting

## Remaining Work

### Next Steps
1. **Create Unit Tests** ✅
   - Test client generation utility
   - Test client registry service
   - Test extractor with mock data

2. **Documentation** ✅
   - Add docstrings to all methods
   - Create usage examples
   - Document fallback behaviors

3. **Performance Optimization**
   - Add caching for frequently used schemas
   - Optimize image processing

### Future Improvements
1. **Streaming Support** ⬜
   - Implement streaming for large array fields
   - Add progress tracking

2. **Caching Layer**
   - Add caching for extraction results

3. **Advanced Metrics**
   - Implement more detailed performance metrics
   - Add cost tracking

## References
- BAML_exploration_v2 directory for examples of working implementations
- BAML documentation at https://docs.boundaryml.com 