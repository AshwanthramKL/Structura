# STRUCTURA – Turning Unstructured Docs into Schema-Tight JSON

> **Mission** Show we can ingest 150 k-token schemas + 10 MB documents and emit JSON that
> passes the desired schema.

---

## 1. Self-contained architecture diagram 🏗️
```markdown
┌─1 RAW INPUTS ─────────────────────────────────────────────────────────┐
│ • Files(Supported)                                                    │
│ • .pdf / .png / .jpeg / .jpg (vision)                                 │
│ • .txt / .md / .bib (text)                                            │
│ • .csv (row splitter)                                                 │
│ • target_schema.json                                                  │
└───────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─2 SCHEMA → BAML (compile once) ─────────────────────────────────────────────────┐
│ extended converter handles arrays, regex, $ref, properties, oneOf, if/then/else │
└──────────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─3 PLANNER (token-aware) ────────────────────────────────────────────────────────┐
│ • OpenAI tiktoken / Gemini countTokens on schema & file                         │
│ • estimate array lengths, token costs                                           │
│ • choose model-tier set via enable_max_mode flag                                │
│ • decide plan:                                                                  │
│ – Vision (pdf/docx/pptx): ToC-LLM → semantic chunks                             │
│ – Text (txt/md): LLM splitter → exact start & end substrings of chunks          │
│ – CSV: row splitter                                                             │
│ • mark oversized arrays as **STREAM** (slice plan)                              │
└─────────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─4 CHUNKER (materialises string/page/row ranges) ──────────────────────────────┐
└───────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─5 EXTRACT + VALIDATE ───────────────────────────────────────────────────┐
│ • one LLM call per 1.chunk or 2.array-slice                             │
│ • BAML validates & auto-repairs                                         │
│ • emits slice JSON + source_ptr                                         │
└─────────────┬───────────────────────────────────────────────────────────┘
              │
              ▼
┌─6 HUMAN QUEUE (ndjson, with source_ptr) ─────────────────────────────┐
└──────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─7 MERGER (safe) ───────────────────────────────────────────────────────┐
│ • integrate unique json objects                                        │
│ • arrays: extend in slice order; verify final length                   │
│ • scalars: conflict → human queue (both values)                        │
│ • final jsonschema check                                               │
└────────────────────────────────────────────────────────────────────────┘
│
▼
┌─8 FINAL JSON (schema-compliant) ───────────────────────────────────────┐
└────────────────────────────────────────────────────────────────────────┘
```

## Numbers 1-8 are referenced throughout the deep-dive.

## 2. Design in one breath 🧘

> **Compile** the schema once, use it as a compact BAML stub; **semantic-chunk** to stay
> under the _input_ window, **stream oversized arrays** to stay under the _output_
> window; validate early, merge late, surface every conflict to a human.

---

## 3. Key references 🔗

1. BAML – https://docs.boundaryml.com/guide/introduction/what-is-baml
2. JSON-Schema→BAML sample (`I'll build on top of this to cover all schema features`) – https://github.com/BoundaryML/baml-examples/tree/main/json-schema-to-baml
3. BAML **Streaming** guide – https://docs.boundaryml.com/guide/baml-basics/streaming (**TBD** experiment verification)
4. Google Gemini countTokens – https://ai.google.dev/api/tokens#method:-models.counttokens
5. OpenAI token management – https://platform.openai.com/docs/advanced-usage#managing-tokens
