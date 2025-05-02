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

| # | Module | Why it exists | Outputs |
|---|---------|--------------|---------|
| **1** | _Raw input loader_ | Normalises file → {bytes, mime, size}. | `DocHandle` |
| **2** | _JSON-Schema → BAML compiler_ | Shrinks verbose schema, injects safety fields. | `schema.baml`, `schema_tok` |
| **3** | _Token-aware planner_ | • Counts tokens (schema + doc)<br>• Finds every **array path**, probes row counts<br>• Chooses model tier via `enable_max_mode`<br>• Emits **ExtractionTask** list (chunk or slice). | list[`ExtractionTask`] |
| **4** | _Chunker_ | Creates semantic string/page/row ranges per chunk when **input** > ctx-window. | list[`Chunk`] |
| **5** | _Extract + Validate (+ Stream)_ | Executes each task:<br> • one-shot for normal arrays<br> • **slice loop** for streamed arrays.<br>Attaches confidence & error paths. | list[`PartialJSON`] |
| **6** | _Human queue_ | NDJSON log – scalar conflicts, low-confidence, unrepaired schema fails. Includes `source_ptr`. | `conflicts.ndjson` |
| **7** | _Merger_ | Concats array slices, checks final length; first-write-wins for scalars, logs conflicts. | `master.json` |
| **8** | _Final validator_ | Final `jsonschema.validate`; 0 errors → deliver. | Success / Fail |

> **Chunking vs Streaming** – chunker protects *input* context; planner/streamer protect *output* token cap.

---

## 3️⃣ Schema → BAML Compiler (Module #2)

### 3.1 Purpose

* Shrink prompt size (~ 40 % under raw JSON-Schema).  
* Leverage BAML runtime’s **auto-repair** for minor JSON glitches.  
* Inject two hidden fields in every object:

```baml
confidence: float @hidden      # model self-score 0-100
unsure?:    "not sure"         # sentinel to avoid hallucinated values
```

### 3.2 Coverage and Algorithm

- Builds on Boundary’s reference converter
https://github.com/BoundaryML/baml-examples/tree/main/json-schema-to-baml.
- Extended support added for: `oneOf`, `anyOf`, `if/then/else`,
`patternProperties`, `top-level regex constraints`.
*Fallback: embed the offending sub-schema verbatim when conversion impossible as a @description.*
- Adds “slice-safe arrays” annotation (BAML comment) so extractor can
supply start_index/limit without violating type rules.
Reference: Boundary docs Streaming guide
https://docs.boundaryml.com/guide/baml-basics/streaming — TBD 

---

## 4️⃣ Token-Aware Planner (Module #3)

### 4.0 Objectives

* guarantee **no input overflow** (⇢ semantic chunking) **and no output overflow**  
  (⇢ per-array **stream slicing**);
* pick the cheapest tier that fits, honouring `enable_max_mode`;
* emit a flat list of **ExtractionTask** records so the extractor can run
  fully async;
* be the single home of all token arithmetic and “how many LLM calls?”

---

### 4.1 Responsibilities

| Task | Explanation |
|------|-------------|
| **Token counting** | `schema_tok` via BAML size, `doc_tok` via tiktoken (OpenAI) or `models.countTokens` (Gemini). |
| **Section enumeration** | Vision → ToC-LLM, Text → LLM based semantic splitter or [semantic chunker](https://docs.llamaindex.ai/en/stable/examples/node_parsers/semantic_chunking/), CSV → header + first-50 rows. |
| **Array probes** | For **each array path** found in the schema, run one cheap LLM to estimate count of the array items(`len(array)`). → `est_len[path]`. |
| **Cost / item** | From schema leaf: numbers = 1 tok, enum = 1 tok, strings ≈ `maxLength / chars_per_tok`, then cached per model family. |
| **Expected-tokens calc** | `sum(cost[path] × est_len[path]) + scalar_meta` → used for tier feasibility & composite score. |
| **Composite complexity score** | `1.0·log2(nodes)+0.6·depth+0.2·enums+0.5·arrays·avgLen+1.0·log2(expectedTok)` (see §4.2). |
| **Tier selection** | Two tier sets:<br> • *normal* = {mini, flash}<br> • *max* = {full, pro}.<br>`enable_max_mode` toggles the set. |
| **Chunk decision** | If `schema_tok + doc_tok > 0.85·C_in` ⇒ build semantic chunks. |
| **Stream decision** | For every array, if `item_cost × est_len > 0.9·tier.max_out` ⇒ mark **stream** & compute `slice_len`. |
| **Task graph output** | Emit `ExtractionTask(chunk_id, path, start, limit, model)`; normal arrays ⇒ one task; streamed arrays ⇒ N slice tasks. |
| **Rows-per-chunk (CSV)** | `rows_cap = floor(0.8 · C_out / avg_row_tok)` (see §4.6). |

---

### 4.2 Composite complexity score

Used only for analytics & future cost models—not for hard routing.
```python
complexity =
1.0 * log2(schema_nodes) +
0.6 * max_nesting_depth +
0.2 * enum_literals +
0.5 * array_fields * avg(est_len) +
1.0 * log2(expected_json_tokens)
```

---

### 4.3 Tier & mode selection logic

```text
if enable_max_mode:
    tiers = [full (32,768), pro (65,536)]
else:
    tiers = [mini (32,768), flash (65,536)]

tier = first tier where expected_json_tokens ≤ 0.9·tier.max_out
if no tier fits → mark arrays that overflow for streaming
```
- full - gpt-4.1
- mini - gpt-4.1-mini
- pro - gemini-2.5-pro
- flash - gemini-2.5-flash

### 4.4 ExtractionTask data structure
```python
ExtractionTask = TypedDict(
    chunk_id   = int,              # 0 if no chunking
    path       = str,              # "invoice.line_items"
    start      = int,              # row offset in array
    limit      = int,              # number of rows to emit
    model_name = str               # "mini" | "flash" | "pro" | "full"
)
```

*Example output for a 2400-row invoice with streaming enabled*
```json
[
    {"chunk_id":0,"path":"invoice.line_items","start":0,"limit":1474,"model":"pro"},  // 1474 rows
    {"chunk_id":0,"path":"invoice.line_items","start":1474,"limit":926,"model":"pro"}, // 926 rows
    {"chunk_id":0,"path":"invoice.comments","start":0,"limit":117,"model":"pro"},     // 117 rows
    {"chunk_id":0,"path":"invoice.comments","start":117,"limit":183,"model":"pro"}    // 183 rows
]
```

### 4.5 Planner pseudocode

```python
def build_plan(doc: DocHandle, schema: dict, enable_max: bool) -> list[ExtractionTask]:
    arrays = find_array_paths(schema)                 # [(path, leaf_schema), …]
    est_len = {p: probe_len(doc.text, p) for p,_ in arrays}
    item_cost = {p: tokens_per_item(leaf, "openai") for p,leaf in arrays}
    exp_tok   = sum(item_cost[p]*est_len[p] for p in arrays) + 128  # scalars

    tier = choose_tier(exp_tok, enable_max)           # may return None if no tier fits
    tasks = []

    # decide chunks (input guard)
    for chunk_id, chunk in enumerate(semantic_chunks(doc, schema_tok=tiktoken.count(schema))):
        for p in arrays:
            max_out = (MAX_OUT[tier] if tier else 32768) * 0.9
            slice_len = max_out // item_cost[p]
            if slice_len >= est_len[p]:               # full array one-shot
                tasks.append(Task(chunk_id,p,0,est_len[p], tier or "flash"))
            else:                                     # array streaming
                for s in range(0, est_len[p], slice_len):
                    tasks.append(Task(chunk_id,p,s,slice_len, tier or "flash"))
    return tasks
```

### 4.4 CSV row sizing

```python
avg_row_tok = count_tokens(csv.first_n_rows(50)) / 50
rows_cap    = floor(0.8 * C_out / avg_row_tok)
```

_Why? Averaging over full rows captures delimiter overhead and numeric cell density better than avg_cell_tok × n_cols._

---

## 5️⃣ Chunkers (Module #4)

> **avoid `input context overflow`** by producing semantically-aligned pieces.  
> `Output-overflow` is now handled by the planner’s **array-streaming** path (§4).

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

## 6️⃣ Extract + Validate (+ Stream) (Module #5)

### 6.1 Execution loop (task-driven)

```python
async def run_tasks(tasks: list[ExtractionTask], schema_baml: str):
    """
    Executes ExtractionTask objects emitted by the planner.
    Yields PartialJSON slices; merger handles assembly.
    """
    async def _call(task: ExtractionTask):
        prompt = build_baml_prompt(
            schema_baml,
            chunk_text=task.chunk.text,
            path=task.path,
            start_index=task.start,
            limit=task.limit
        )
        llm_resp = await llm_generate(
            model=task.model_name,
            prompt=prompt,
            max_tokens=int(0.95 * MAX_OUT[task.model_name])
        )
        obj, _ = baml.parse(llm_resp)          # auto-repair inside
        fail = [e.relative_path for e in validator.iter_errors(obj)]
        return PartialJSON(
            obj=obj,
            source_ptr=f"{task.chunk.src}#slice={task.start}/{task.limit}",
            fail_paths=fail,
        )

    # run all tasks concurrently
    return await asyncio.gather(*[_call(t) for t in tasks])
```
*BAML prompt stub (`build_baml_prompt`) injects four parameters: `doc`, `path`, `start_index`, `limit`.*

This mirrors the Streaming example in Boundary docs (TBD → hands-on validation).

### 6.2 Percentile scaling and final score

After all chunks/tasks finish we normalise the set
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

### 7.1 Merge rules
```python
def merge(master, partial, ptr):
    # arrays → append slice
    for path, slice_ in partial.get_arrays():
        arr = master.setdefault(path, [])
        arr.extend(slice_)
    # scalars → first-write wins, log conflicts and send to human
    for path, val in partial.get_scalars():
        if path not in master:
            master[path] = val
        elif master[path] != val:
            log_conflict({
                "json_path": path,
                "existing": master[path],
                "incoming": val,
                "source_ptr_existing": ptr_existing[path],
                "source_ptr_incoming": partial.source_ptr,
            })
```

After final slice arrives the merger asserts:

```python
assert len(master["invoice"]["line_items"]) == planner_est["invoice.line_items"]
```

### 7.2 Human-queue record format
```json
{
  "json_path": "invoice.vendor",
  "existing": "ACME",
  "incoming": "ACE",
  "source_ptr_existing": "pdf#page=3",
  "source_ptr_incoming": "pdf#page=7",
  "reason": "scalar_conflict"
}
```

### 7.3 Queue triggers
| Trigger                    | Reason                                                       |
| -------------------------- | ------------------------------------------------------------ |
| `confidence < 0.5`         | Model self-doubt.                                            |
| scalar conflict            | Business decision required.                                  |
| unrepaired schema fail     | Deterministic validation error.                              |
| **slice\_count\_mismatch** | Final array shorter/longer than probe (streaming integrity). |

*Queue stored as append-only NDJSON; source_ptr gives reviewers a deep link.*

---

## 8️⃣ Merger & Final Validator

### 8.1 Merge algorithm

```python
def merge(master, partial):
    # ── 1. Scalars ──────
    for ptr, val in partial.get_scalars():
        if ptr not in master:
            master[ptr] = val
        elif master[ptr] != val:  # conflict
            log_conflict({
               "json_path": ptr,
               "existing": master[ptr],
               "incoming": val,
               "source_ptr_existing": src_map[ptr],
               "source_ptr_incoming": partial.source_ptr
            })
    # ── 2. Arrays (slice streaming) ──────
    for ptr, slice_ in partial.get_arrays():
        master.setdefault(ptr, []).extend(slice_)
        slice_count[ptr] += len(slice_)
```
After all tasks finish the merger asserts:

```python
for ptr, expected in planner_est_counts.items():
    if len(master.get(ptr, [])) != expected:
        log_conflict({
          "json_path": ptr,
          "reason": "slice_count_mismatch",
          "expected": expected,
          "actual": len(master.get(ptr, []))
        })
```

Scalar conflicts and slice-count mismatches are the two cases that push
records to the human queue.

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
| **4** | **Slice Completeness**             | Final array shorter/longer than probe (streaming integrity).                                                                                       | arrays_ok / arrays_total where ok = final length = probe                        | Streaming correctness.                                                     |
| **5** | **Confidence Calibration** (Brier) | Model outputs `conf=0.9` on 100 fields but 20 are wrong.<br> Brier ≈ 0.18 (bad).                                                                  | $$\textstyle \frac1N\sum (p_i - y_i)^2$$ on raw_conf (before scaling).           | Tells us whether we can trust the numeric confidence to triage work.       |
| **6** | **Human-Touch Rate**               | Out of 500 JSON paths, 42 land in `conflicts.ndjson` ➜ HTR = 0.084.                                                                               | `manual_paths / total_paths`.                                                    | Operational cost metric—lower = cheaper for client support team.           |

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

---
