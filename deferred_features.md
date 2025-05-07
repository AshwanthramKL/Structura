# Deferred Features for Structura Prototype V1

The following features have been intentionally deferred for the initial prototype to meet time constraints.

## Array Streaming
- **Status:** Deferred to future version
- **Description:** Breaking large arrays into manageable slices for processing
- **Reason:** Initial prototype focuses on documents that fit within context window
- **Future Implementation:** Will follow approach in Architecture.md §4.5

## Complex Confidence Scoring
- **Status:** Deferred to future version
- **Description:** Percentile scaling and blending of confidence scores
- **Reason:** Basic extraction without confidence tracking is sufficient for prototype
- **Future Implementation:** Will follow approach in Architecture.md §6.2

## Human Queue with Complex Conflict Resolution
- **Status:** Simplified for prototype (basic logging only)
- **Description:** Full NDJSON logging with source pointers and detailed reason codes
- **Reason:** Basic merge conflicts are handled without complex resolution
- **Future Implementation:** Will follow approach in Architecture.md §7.2-7.3

## Evaluation Metrics
- **Status:** Deferred to future version
- **Description:** Schema-Pass Rate, Field-Level F1, Hallucination Score, etc.
- **Reason:** Focus on core extraction pipeline for prototype
- **Future Implementation:** Will follow approach in Architecture.md §9.1-9.4

## Vision-Based PDF Chunking
- **Status:** Simplified for prototype
- **Description:** ToC-LLM approach for semantic chunking of PDFs
- **Reason:** Initial implementation focuses on text-based chunking with LlamaIndex
- **Future Implementation:** Will follow approach in Architecture.md §5.1

## Array Probes for Length Estimation
- **Status:** Simplified for prototype
- **Description:** Using LLM to estimate array lengths for planning
- **Reason:** Initial implementation uses simpler heuristics for array estimation
- **Future Implementation:** Will follow approach in Architecture.md §4.1

## Additional File Type Support
- **Status:** Limited for prototype
- **Description:** Support for DOCX, PPTX, and other file formats
- **Reason:** Initial focus on TXT, MD, and basic PDF support
- **Future Implementation:** Mentioned in Future Milestones section of Prototype_Scope.md 