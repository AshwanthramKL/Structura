# STRUCTURA – Technical Architecture

The goal is clear:

_Ingest arbitrary long documents (PDF, TXT, CSV) + 150 k-token schemas and emit JSON that **passes the schema first try** – flagging anything dubious for
humans._

The system is intentionally modular so each concern (token limits, validation,
merging) can evolve independently.

---

## 0️⃣ Technology Stack & Rationale

| Piece                                                                 | Why chosen                                                                                                                                                                                                                   | Alternatives (why dropped)                                                                                                                                                                                                                                                                                                       |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **BAML** – boundaryml DSL + runtime <https://docs.boundaryml.com>     | • Structured-output focused DSL<br>• Parser based rather than followup-message based (saves cost/latency)<br>• Vast Model Support<br>• Good documentation<br>• Validation from Developers on Reddit<br>• Personal preference | **[dottxt-outline](https://dottxt-ai.github.io/outlines/latest/)** (supports only Open-weight models and OpenAI)<br>**[ELLM](https://docs.ell.so/core_concepts/multimodality.html)** (not under active development-last commit 3 months ago)<br>**[DSpy](https://dspy.ai/)** (close second, personal preference to leave it out) |
| **OpenAI GPT-4.1 series** & **Google Gemini 2.5 series**              | • Cheapest and Smartest in their class<br>• 1M context window<br>• 32k & 64k output tokens respectively<br>• Yielded best results in my experiments                                                                          | Claude 3.7 Sonnet (200k ctx)<br>GPT-4o (128k context, 16k output tokens, and 4.1 was better)                                                                                                                                                                                                                                     |
| **`jsonschema`** ref-impl <https://python-jsonschema.readthedocs.io/> | • Returns **all failing paths**, not just first violation                                                                                                                                                                    | `fastjsonschema` (stops at first error)                                                                                                                                                                                                                                                                                          |

---

## 1️⃣ Notation

| Symbol  | Meaning                                                       |
| ------- | ------------------------------------------------------------- |
| `T_in`  | total prompt tokens (`schema_tok + chunk_tok + model_prompt`) |
| `T_out` | expected output tokens                                        |
| `C_in`  | model input limit (`context window`)                          |
| `C_out` | model output limit (`max_tokens`)                             |

Guards: **`T_in ≤ 0.85 * C_in`** and **`T_out ≤ 0.95 * C_out`**  
(wiggle room based on variable tokenizers).

---

## 2️⃣ Data-flow in prose ([Overview diagram](docs/1_Overview.md#self-contained-architecture-diagram-🏗️))

| #     | Module                      | Why it exists                                                                        | Outputs                               |
| ----- | --------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------- |
| **1** | _Raw input loader_          | Normalises file → {bytes, mime, size}.                                               | `DocHandle`                           |
| **2** | _JSON Schema→BAML compiler_ | Turn verbose JSON-Schema into compact BAML schema & inject safety fields.            | `schema.baml`, `schema_tok`           |
| **3** | _Token-aware planner_       | Picks model tier, decides chunk boundaries, prevents running out of `output tokens`. | list[`PlanChunk`]                     |
| **4** | _Chunker_                   | Materialises string/page/row ranges per chunk.                                       | list[`Chunk`] with `text` or `images` |
| **5** | _Extract + Validate loop_   | One LLM call per chunk; attaches confidence & error paths.                           | list[`PartialJSON`]                   |
| **6** | _Human queue_               | NDJSON log for duplicates, low-confidence, schema fails to be resolved by humans.    | `conflicts.ndjson`                    |
| **7** | _Merger_                    | Stitch partials; never overwrite without review.                                     | `master.json`                         |
| **8** | _Final validator_           | Last `jsonschema.validate`; 0 errors → deliver.                                      | Success / Fail                        |

---

## 3️⃣ Schema → BAML Compiler (Module #2)

### 3.1 Purpose

- Minimise prompt size (~40 % smaller than raw schema).
- Allow BAML runtime to **auto-repair** minor JSON glitches.
- Inject **two synthetic fields** into every _object_ class:

```baml
  confidence: float @hidden      # model self-score 0-100
  unsure?: "not sure"            # sentinel enum entry to mitigate hallucination or schema violations
```

### 3.2 Algorithm

Will build on top of this [JSON schema to BAML compiler](https://github.com/BoundaryML/baml-examples/tree/main/json-schema-to-baml)

Currently doesn't cover all the features of JSON schema such as `if_then_else`, `anyOf`, `oneOf`, `regex` etc.

---

## 4️⃣ Token-Aware Planner (Module #3)

### 4.0 Why Chunking in the first place?

- If JSON schema runs upto 150k as mentioned in the assgn, then we'll run out of output tokens if a big document is passed to the system or if there are arrays in the schema.
- Preventing single point of failure. If a chunk fails, we can still extract the rest of the document and retry the failed chunk.

### 4.1 Why a separate planner?

1. Context & output limits differ by model/vendor → we must compute both.
2. Splitting logic (pages vs. semantic text vs. rows) is doc-type-specific; isolating planner keeps extractor simple.
3. Planner can later grow cost-based model selection (Flash → Pro) without touching chunkers.

### 4.2 Responsibilities

| Task                         | Explanation                                                                                                                                                                                                                                                                                                                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Token counting**           | `schema_tok = tiktoken.count()` (OpenAI) or `models.countTokens(schema)` (Gemini)                                                                                                                                                                                                                                                                                                    |
| **Section enumeration**      | Vision: run TOC-LLM to generate a table of contents and split the pages into sections(this is done to ensure cross-page context is maintained while extracting); Text: run splitter-LLM to split the text into sections based on semantic boundaries([semantic chunker](https://docs.llamaindex.ai/en/stable/examples/node_parsers/semantic_chunking/)); CSV: read header + 50 rows. |
| **Guard #1**                 | Keep prompt ≤ 85 % `C_in` to allow for mis-counts or variable tokenization.                                                                                                                                                                                                                                                                                                          |
| **Guard #2**                 | Ensure expected JSON ≤ 95 % `C_out`.                                                                                                                                                                                                                                                                                                                                                 |
| **Array-explosion estimate** | Ask small LLM: “How many `<array_field>` items present?”; multiply by item token size.                                                                                                                                                                                                                                                                                               |
| **Rows-per-chunk (CSV)**     | `rows_cap = floor(0.8 * C_out / (avg_cell_tok * n_cols))`                                                                                                                                                                                                                                                                                                                            |

> Note:  
> Array-explosion: A JSON schema can have an array field like "line_items":  
> { "type":"array", "items":{…} }.  
> Input doc may list 5 000 items ⇒ output easily 200 k tokens though the doc text is short.  
> Planner therefore estimates array length first to pick model or chunk.

### 4.3 End-to-end algorithm

```python
def plan_document(doc: DocHandle, schema_tok: int) -> list[PlanChunk]:
    """
    Decide model tier + chunk boundaries.
    Returns empty list when no chunking required.
    """
    caps = choose_model(schema_tok, doc.size)        # GPT-4.1 vs Gemini
    doc_tok = count_tokens(doc)                      # whole file first!

    # ── Fast path: fits in one shot ───────────────────────────────
    if (schema_tok + doc_tok) <= 0.85 * caps.C_in:
        exp_out = estimate_output(doc)               # scalar + arrays
        if exp_out <= 0.95 * caps.C_out:
            return [PlanChunk(doc_range=doc.all(), model=caps.name)]

    # ── Slow path: need chunking ─────────────────────────────────
    sections = enumerate_sections(doc)               # Vision TOC or Text splitter
    chunks: list[PlanChunk] = []
    cur: list[Section] = []; cur_tok = 0

    for sec in sections:
        if schema_tok + cur_tok + sec.tok > 0.85 * caps.C_in:
            chunks.append(PlanChunk(cur, caps.name))
            cur, cur_tok = [], 0
        cur.append(sec); cur_tok += sec.tok

    if cur: chunks.append(PlanChunk(cur, caps.name))
    return chunks
```

### 4.4 CSV row sizing (updated)

```python
avg_row_tok = count_tokens(csv.first_n_rows(50)) / 50
rows_cap    = floor(0.8 * C_out / avg_row_tok)
```

_Why? Averaging over full rows captures delimiter overhead and numeric cell density better than avg_cell_tok × n_cols._

---

## 5️⃣ Chunkers (Module #4)

### 5.1 Vision ToC-LLM splitter

**Input:** Entire PDF/document.  
**Why ToC first?**  
Most long PDFs have natural section headings; keeping page-ranges aligned to
those headings preserves cross-page context (figures, continued tables).

_eg. setting of an experiment maybe defined in page 1 and the results in page 2._

1. **Gemini Flash Vision prompt**

```text
"Return JSON [{title,start_page,end_page,refs_next_or_null}] …"
```

2. **Neighbour grouping**

```python
for i,sec in enumerate(toc):
    group.append(sec)
    if (sec.refs_next == toc[i+1].title) or would_break_guard(next_sec): # break if next section is not the same as the current section
        continue
    yield group; group = []
```

3. **Example**

| title    | p_start | p_end | refs_next |
| -------- | ------- | ----- | --------- |
| Intro    | 1       | 2     | null      |
| HW       | 3       | 5     | Safety    |
| Safety   | 6       | 7     | null      |
| Warranty | 8       | 8     | null      |

→ Planner outputs chunks: [Intro], [HW+Safety], [Warranty].

### 5.2 Text LLM splitter

**Input:** raw UTF-8 text (e.g. .txt / .md / .bib).  
**Prompt:** GPT-4.1-mini or Gemini 2.5-flash

```javascript
You are a segmenter…

Return JSON array of blocks:
  { "title": "<heading-or-null>",
    "start_string": <string>,
    "end_string": <string> }

I'd like you to draw semantic boundaries and return chunks in the format of a ToC.
Note that I'd like each boundary to be a minimum of a paragraph long and maximum of 3-4 paragraphs long.
Make sure not to leave out even a single character. beware of string escape characters and special characters.

<<full doc content>>
```

> **Research note:**
> If string matching using `start_string` and `end_string` string matching in the prompt fails, will use `semantic-chunking` via [LlamaIndex](https://docs.llamaindex.ai/en/stable/examples/node_parsers/semantic_chunking/).

### 5.3 CSV splitter – detailed

Pre-scan header + first 50 rows → avg_row_tok.

Compute rows_cap (see §4.4).

Produce contiguous row-blocks:

```python
chunk_0 = rows[0 : rows_cap]
chunk_1 = rows[rows_cap : 2*rows_cap]
…
```

Header is prepended to every chunk so the LLM always sees column names.

```python
for i in range(0, len(rows), rows_cap):
    yield [header] + rows[i:i+rows_cap]
```

---

## 6️⃣ Extract + Validate (Module #5)

### 6.1 End-to-end flow per chunk

```python
async def extract_validate(chunk: Chunk, schema_baml: str, caps: ModelCaps):
    """
    Returns PartialJSON(record), raw_conf, lib_conf, final_conf, fail_paths
    """
    # 1) Build prompt
    prompt = build_baml_prompt(schema_baml, chunk.content)

    # 2) Call LLM (async)
    llm_resp = await llm_generate(prompt, max_tokens=int(0.95 * caps.C_out))

    # 3) BAML parses & auto-repairs
    obj, _ = baml_runtime.parse(llm_resp)        # _ = parse_conf not used

    # 4) Schema validation
    fail_paths = [e.relative_path for e in validator.iter_errors(obj)]
    lib_conf   = 1.0 if not fail_paths else 0.0  # deterministic

    # 5) Self-confidence from the model (may be inflated)
    raw_conf = obj.pop("confidence", 0.5)        # 0–1 range by prompt instruction
    return PartialJSON(obj, raw_conf, lib_conf, fail_paths)
```

### 6.2 Percentile scaling and final score

After all chunks finish we normalise the set
`{raw_conf_i} → raw_conf_scaled_i` via percentile mapping so that:

- lowest raw_conf → 0
- median raw_conf → 0.5
- highest raw_conf → 1

This curbs models that habitually output high confidence(0.9) for everything.

```python
def blend_conf(raw_conf_scaled: float, lib_conf: float) -> float:
    """
    Final confidence = 0.7 * lib_conf  +  0.3 * raw_conf_scaled
    Validator gets higher weight because it is deterministic.
    """
    return 0.7 * lib_conf + 0.3 * raw_conf_scaled
```

_Why no scaling for lib_conf?  
It is already a binary, deterministic measure (schema pass = 1, fail = 0).
Applying percentile scaling would distort that ground-truth signal._

Sample aggregated record

```json
{
  "chunk_id": 2,
  "data": { "runs-on": "ubuntu-latest" },
  "raw_confidence": 0.82,
  "raw_confidence_scaled": 0.76,
  "lib_confidence": 1.0,
  "final_confidence": 0.83,
  "fail_paths": []
}
```

If fail_paths is non-empty the record is auto-queued for Human review
(regardless of final_confidence).

---

## 7️⃣ Human Queue (Module #6)

Humans intervene only where automation could silently corrupt data.

- **Why NDJSON?** Append-only log, grep-able, easy to load into Excel/Airtable.
- **When is a record queued?**

| Trigger                                    | Reason                                  |
| ------------------------------------------ | --------------------------------------- |
| confidence < threshold(0.5 for now)        | Model uncertain or schema fail penalty. |
| duplicate ptr, different value             | Need business decision.                 |
| `jsonschema` violation not auto-repairable | Model couldn’t satisfy schema.          |

---

## 8️⃣ Merger & Final Validator

### 8.1 Merge algorithm

```python
for ptr, val in walk_json(partial.data):
    if ptr not in master:
        master[ptr] = val                   # first arrival wins
    elif master[ptr] != val:
        log_conflict(ptr, master[ptr], val) # sent to human

# arrays - append
for arr_ptr, slice_ in partial.get_arrays():
    master.setdefault(arr_ptr, []).extend(slice_)
```

_We **do not hidden-concat duplicates of scalar paths**; every conflict goes to humans._

### 8.2 Final check

```python
try:
    validator.validate(master)
except ValidationError as e:
    raise SystemExit(f"Delivery blocked: {e.message}")
```

---

## 9️⃣ Evaluation

We score the system on two axes:

- **A – Schema compliance** – “Does the JSON even compile against the schema?”
- **B – Extraction fidelity** – “Is every extracted value correct?”

### 9.1 Metrics (with toy examples)

| #     | Metric                             | Tiny example                                                                                                                                      | How we compute it                                                                | Why we need it                                                             |
| ----- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **1** | **Schema-Pass Rate**               | Chunk JSON `{ "runs-on": "ubunut" }` fails schema (enum mismatch) ➜ counted **fail**.<br> Auto-repair corrects to `"ubuntu-latest"` ➜ **pass**.   | `ok_chunks / total_chunks` after BAML auto-repair.                               | If this isn’t ≈ 1.0 downstream code will crash—hard P0 KPI.                |
| **2** | **Field-Level F1**                 | Gold: `"batch_size": 32`.<br> Extracted: `30`.<br> → 1 false-neg (miss) + 1 false-pos (wrong value).<br> Precision = 0.5, Recall = 0.5, F1 = 0.5. | Exact string match for scalars; Jaccard for arrays; micro-averaged over corpus.  | Direct quality signal for recruiters: higher = fewer content errors.       |
| **3** | **Hallucination Score**            | Extracted JSON contains DOI `"10.1234/ghost"`, which never appears in source PDF. ➜ counts toward hallucination.                                  | LLM grader (see below) flags unsupported values → `hallucinated / total_values`. | Proves extractor is “ copy-not-invent” – critical for compliance & audits. |
| **4** | **Confidence Calibration** (Brier) | Model outputs `conf=0.9` on 100 fields but 20 are wrong.<br> Brier ≈ 0.18 (bad).                                                                  | $$\textstyle \frac1N\sum (p_i - y_i)^2$$ on raw_conf (before scaling).           | Tells us whether we can trust the numeric confidence to triage work.       |
| **5** | **Human-Touch Rate**               | Out of 500 JSON paths, 42 land in `conflicts.ndjson` ➜ HTR = 0.084.                                                                               | `manual_paths / total_paths`.                                                    | Operational cost metric—lower = cheaper for client support team.           |

### 9.2 LLM grader for Hallucination & Field-F1

```python
grader_prompt = """
You are a strict evaluator. Given ORIGINAL_DOC and extracted JSON_OUTPUT,
list any values in JSON_OUTPUT that are not justified by the text, and any
gold values missing. Return JSON:
{ issues: [ {path:str, kind:"FP|FN", snippet:str} ] }
"""
issues = call_judge_llm(
    grader_prompt.format(ORIGINAL_DOC=chunk_text,
                         JSON_OUTPUT=partial_json))
```

- **False Positive (FP)** → value present in output but absent in doc.
- **False Negative (FN)** → value present in gold but missing in output.

Field-F1 is then computed as:

```
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
```

_Sanity check: We first run the grader on 100 gold pairs; if its own precision ≥ 0.9 we trust its judgments._

### 9.3 Confidence scaling logic (why only scale raw_conf)

- **raw_conf (model self-score) can be inflated (“everything is 0.9”).**
  We percentile-scale only this number to spread it 0-1.

- **lib_conf is deterministic: 1 = schema pass, 0 = fail. Scaling would destroy that binary truth.**

- **Final blended score per chunk**

```python
final_conf = 0.7 * lib_conf + 0.3 * scaled_raw_conf
```

A chunk that passes schema but where the model is unsure (0.3 scaled) still gets a healthy 0.61; a schema-fail forces ≤ 0.3.

### 9.4 Metric importance ranking

- **Schema-Pass Rate** – hard gate; delivery blocker.

- **Field-Level F1** – true extraction accuracy.

- **Hallucination Score** – safeguards data integrity & compliance.

- **Confidence Calibration** – makes human-in-the-loop cost-effective.

- **Human-Touch Rate** – operational, useful for ROI projections.

---

## 🔟 Future Prospects

### 10.1 Fine-tune GPT-4.1-mini with collected chunks

| Benefit        | Detail                                                                         |
| -------------- | ------------------------------------------------------------------------------ |
| **Cost ↓**     | Mini tier is already cheap; fine-tune narrows gap by allowing shorter prompts. |
| **Latency ↓**  | Smaller model + fewer repair loops.                                            |
| **Accuracy ↑** | Fine-tuning improves adherence to the desired output schema.                   |

#### Plan

1. **Data collection** – every approved Human-Queue record plus its raw chunk
   saved as {prompt, output} pair (target ≈ 50 k examples).

   > Note: for this we need to limit `max_output_token` of gemini models to 32k(4.1's limit) as well.

2. **Supervised fine-tune** via OpenAI Fine-Tuning API

> If unable to gather 50k examples, we can resort to `distillation`, i.e first fine-tune `gpt-4.1` and then distill it's responses into `gpt-4.1-mini`.

### 10.2 Additional upgrades

| Idea                          | Impact                                        |
| ----------------------------- | --------------------------------------------- |
| **Dynamic model tier switch** | Auto-swap Flash → Pro only when guards break. |

---
