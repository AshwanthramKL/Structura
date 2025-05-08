## Experiments

| ID                                 | Hypothesis / Question                                        | Dataset slice & scale                                       | Method                                                                   | Pass / fail KPI                                             | Why we cares                                    |
| ---------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------- | ----------------------------------------------- |
| **E-1 : Validity Δ and accuracy boost**               | _Does BAML meaningfully raise the % of JSON that validates?_ | 60 docs (3 genres × 20) with gold JSON                      | For each doc:<br> • Raw prompt + JSON-Schema block<br> • BAML DSL prompt | **Schema-Pass Rate** ↑ ≥ 8 pp, **Field-F1** ↑ ≥ 4 pp vs raw | Proves quality gain justifies DSL adoption      |
| **E-2 : Schema-size break-point**  | _At what schema-tokens does output consistency collapse?_    | 6 synthetic schemas: 10 k → 200 k raw (≈4 k→80 k BAML)      | Generate 100-row CSV; measure Pass-Rate & F1 while schema grows          | Identify “cliff” token count; expect stable ≤ 80 k BAML     | Shows whether 150 k real schemas still safe     |
| **E-3 : Array-length break-point** | _When must we switch to slice streaming?_                    | Fix schema; increment `line_items` 100 → 10 000             | Run planner; record first length where one-shot > 0.9·tier.max_out       | Table of {tier, max_rows_one_shot}                          | Quantifies stream threshold, feeds cost sheet   |
| **E-4 : Auto-repair ceiling**      | _SAP fixes syntax errors but not semantic `oneOf`._          | 100 generated JSONs with: 60 syntax glitches, 40 semantic   | Pipe through `baml.parse`, log “repaired vs raise”                       | ≥95 % fix on syntax, ≤10 % on semantic                      | Sets realistic expectation; may add retry logic |
| **E-5 : Compiler robustness(More of a QA)**      | _Can JSON-Schema→BAML handle edge keywords?_                 | 20 public schemas with `patternProperties`, `if/then`, etc. | Run converter; diff raw vs reconverted JSON                              | 100 % structural equivalence or explicit fallback           | De-risks tooling; surfaces manual-edit cases    |

this are the list of exps I have down my pipeline.

---
## “What happens when ?…”:
|                                   | **Small doc** (≤50 pp)   | **Large doc** (100 pp / 10 MB)                                               |
| --------------------------------- | ------------------------ | ---------------------------------------------------------------------------- |
| **Small schema** (≤10 k BAML tok) | **One-shot, mini tier**  | **Chunk input**, still one-shot arrays                                       |
| **Large schema** (80 k BAML tok)  | **One-shot, flash tier** | **Chunk + Stream**: semantic splitter for input, per-array slices for output |

(Visually this goes on a slide; Y-axis = doc size → chunking; X-axis = schema size → streaming.)

---

## Dependency graph & effort per component

| Order | Component (deliverable)                        | Depends on | Why we need it **before** the next thing                                   | Est. time |
| ----- | ---------------------------------------------- | ---------- | -------------------------------------------------------------------------- | --------- |
| **0** | **Doc loader** (txt / md / PDF-to-text¹ / CSV) | —          | Gives raw text to every later stage                                        | **1 h**   |
| **1** | **`jsonschema` validator harness**             | —          | Used by compiler-tests **and** E-1 validity experiment                     | **1 h**   |
| **2** | **Schema → BAML compiler** (extended keywords) | 1          | Must exist to: (a) build prompts, (b) run E-1 / E-2                        | **1.5 h** |
| **3** | **Synthetic / sample schemas + gold JSON**     | 1          | Needed to unit-test compiler & feed experiments                            | **0.5 h** |
| **4** | **Planner** (token maths + slice emitter)      | 2          | Produces `ExtractionTask` list for extractor; E-3 break-point relies on it | **3 h**   |
| **5** | **Chunkers** (Vision + text + CSV)             | 0          | Planner calls them when `doc_tok` > 0.85 · C\_in                           | **2 h**   |
| **6** | **Extractor (+ BAML slice prompt)**            | 2 4        | Needs compiled schema and task list                                        | **3 h**   |
| **7** | **Merger + slice count assert**                | 6          | Consumes PartialJSON slices; feeds human-queue stub                        | **1 h**   |
| **8** | **Experiment harness** (E-1…E-4 scripts)       | 1 2 4 6    | Runs comparative tests and logs KPIs                                       | **1.5 h** |
