# 3_Prototype_Scope.md

The prototype aims to **prove feasibility** and give Metaforms an interactive demo
in limited time. Everything else is flagged as negotiable or postponed. (**NOTE: `@Siddish` need your approval to proceed**)

| Bucket                   | **Must-have (PoC)**                                                                                                                                                                                                 | **Agree-with-Recruiter** | **Out-of-scope v1**                               | **Description / Comments**                                                                                                                                                                             |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Input handling**       | • PDF/Images through Vision<br>• TXT/MD/BIB through Text<br>• CSV                                                                                                                                                   | —                        | DOC/X, PPT/X, RST, Other UTF-8 files, source-code | Supports all file types listed in assignment; others need bespoke parsers(eg. [AST parser](https://github.com/cedricrupb/code_ast?tab=readme-ov-file) for code), hence skipped due to time constraints |
| **Schema → BAML**        | arrays, regex, `$ref`, `anyOf/oneOf`, `if/then/else`, `additionalProperties`, large enums, **synthetic `confidence` + `unsure` fields**                                                                             | —                        | —                                                 | Achieves _full_ JSON-Schema coverage expected by test cases.                                                                                                                                           |
| **Planner**              | Token counting (OpenAI `tiktoken`, Gemini `countTokens`); dual guards (85 % in / 95 % out); array streaming planner; CSV row sizing;                                                                                | —                        | -                                                 | Planner owns all token maths; extractor never worries about limits.                                                                                                                                    |
| **Chunkers**             | • Vision → TOC-LLM + neighbour grouping<br>• Text → LLM splitter (start&end strings/[semantic chunker](https://docs.llamaindex.ai/en/stable/examples/node_parsers/semantic_chunking/))<br>• CSV → rows_cap splitter | —                        | Table extraction, code AST splitter               | Keeps cross-page semantics;                                                                                                                                                                            |
| **Extractor + Validate** | Async LLM calls; BAML auto-repair; slice extraction when flagged; jsonschema full-path errors; **dual confidence** (raw, validator) + percentile scaling                                                            | —                        | Secondary verifier model; self-healing retries    | —                                                                                                                                                                                                      |
| **Merger**               | First-write wins; conflicting scalars → Human queue; array concat with len-check; final jsonschema check                                                                                                            | —                        | —                                                 | Guarantees no silent overwrite; human-in-the-loop for safety.                                                                                                                                          |
| **Human Queue**          | NDJSON log (`logs/conflicts.ndjson`)                                                                                                                                                                                | —                        | —                                                 | Text/CSV/NDJSON file good enough for demo; UI can be added later.                                                                                                                                      |

---

# Future milestones (post-demo)

- Additional parsers for DOC/X, PPT/X, code (AST based parser).
- Evaluation metrics.
- Minimal UI for Human-Queue resolution.
- Fine-tune GPT-4.1-mini on approved chunks → cost & latency ↓.
- Explore a `2-stage pipeline` where for reasoning intensive tasks, we first fetch the answer in NL and then extract the JSON from the NL. [Source1](https://arxiv.org/pdf/2408.02442), [Source2](https://www.instill-ai.com/blog/llm-structured-outputs)

  - **Why this won't be implemented in this prototype:**
    - First, have to perform EDA(for our usecase) to find out split between reasoning intensive and non-reasoning intensive tasks.
    - A reasoning intensive task in this appln: there exists a field in the schema that requires us to perform some calculations based on the values of other fields. eg. Total Bill value, CGST, SGST, provided in the bill, but we also need to calculate Taxable Value, IGST, etc.
    - Experiment to find if the claim made in the paper is true or not.
    - Then add a layer to determine if a task is reasoning intensive or not and perform `routing` based on that.

  Basically, due to time constraints, we won't be able to experiment(_also don't know if you guys have enough data points to perform EDA_) and implement this in this prototype.
