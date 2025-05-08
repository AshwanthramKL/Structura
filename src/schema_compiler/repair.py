"""schema_compiler.repair
========================
Schema-aware auto-repair utilities used by Extractor (and future Merger).

The public entry point is ``normalize(data, schema)`` which tries to coerce
LLM output into a structure that validates against *schema*.

Prototype scope / limitations (2025-05-08)
------------------------------------------
* union handling: picks the first branch that is either explicitly an
  ``object`` or the first branch overall – **does not** run full validation.
* complex formats (email, date, etc.) and the ``format`` keyword are ignored.
* External ``$ref``s are assumed to be resolved by the Converter beforehand.

Despite these limitations it already covers the common cases responsible for
most validation errors in the prototype: missing required keys, ``null``/"" vs
object/boolean discrepancies, simple enum/const defaults, and key-value
shorthands such as ``key: description``.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_to_dict(text: str) -> Any:
    """Attempt to turn *text* into a Python object.

    Tries JSON first, then YAML (if available), finally a very naive
    ``key: value`` splitter that returns a dict suitable for GitHub-Action
    ``outputs`` shorthand.
    """
    text = text.strip()
    # Fast-path: JSON object
    if text.startswith("{"):
        try:
            return json.loads(text)
        except Exception:
            pass
    # YAML fall-back – only if pyyaml is present to avoid new dependency
    if ":" in text:
        try:
            import yaml  # type: ignore

            return yaml.safe_load(text)  # can yield dict, list, etc.
        except Exception:
            # last-chance: key: value → {key: value}
            key, _, val = text.partition(":")
            key = key.strip().lstrip("{").rstrip("}").strip().strip("'\"")
            val = val.strip().strip("'\"")
            if key:
                return {key: val}
    return text  # give up – return as-is


def _coerce_empty(value: Any, subschema: Dict[str, Any]) -> Any:
    """Return a sensible default when *value* is the empty string."""
    if value != "":
        return value
    expected = subschema.get("type")
    if isinstance(expected, list):
        expected = next((t for t in expected if t != "null"), None)
    if expected in (None, "object") or {
        k for k in ("properties", "patternProperties", "additionalProperties")
    } & subschema.keys():
        return {}
    if expected == "boolean":
        return False
    if expected in ("number", "integer"):
        return 0
    if expected == "string":
        pattern = subschema.get("pattern", "")
        if "${{" in pattern:
            return "${{ PLACEHOLDER }}"
        elif pattern:
            return "PLACEHOLDER"
    return value  # leave untouched


def _pick_union_branch(data: Any, union_schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Select a branch of ``oneOf``/``anyOf`` to use for coercion.

    Heuristic: if *data* is dict-like (including empty string) prefer a branch
    whose type is ``object`` or has object-ish keys; otherwise take the first.
    """
    for sch in union_schemas:
        t = sch.get("type")
        if t == "object" or (
            t is None and (
                "properties" in sch or "patternProperties" in sch or "additionalProperties" in sch
            )
        ):
            return sch
    return union_schemas[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize(data: Any, schema: Dict[str, Any]) -> Any:  # noqa: C901  (complexity)
    """Recursively normalise *data* according to *schema*."""
    # 1. Handle unions early
    if "oneOf" in schema:
        schema = _pick_union_branch(data, schema["oneOf"])
    if "anyOf" in schema:
        schema = _pick_union_branch(data, schema["anyOf"])

    schema_type: Optional[str | List[str]] = schema.get("type")
    if isinstance(schema_type, list):
        # remove redundant "null"; take the first non-null as primary
        schema_type = next((t for t in schema_type if t != "null"), None)

    # 2. Object handling -----------------------------------------------------
    if schema_type == "object" or (
        schema_type is None and (
            "properties" in schema or "patternProperties" in schema or "additionalProperties" in schema
        )
    ):
        if data is None or data == "":
            data = {}
        # Attempt to parse strings that look like dicts
        if isinstance(data, str):
            data = _parse_to_dict(data)
            if not isinstance(data, dict):  # still not dict → force empty
                data = {}
        if not isinstance(data, dict):
            # type mismatch → replace with empty dict so required keys will be filled
            data = {}
        props = schema.get("properties", {})
        pat_props = schema.get("patternProperties", {})
        required = set(schema.get("required", []))
        out: Dict[str, Any] = {}
        for k, v in data.items():
            # coerce "" according to subschema
            subschema = props.get(k)
            if subschema is None:
                for pattern, p_sch in pat_props.items():
                    try:
                        if re.match(pattern, k):
                            subschema = p_sch
                            break
                    except re.error:
                        continue
            subschema = subschema or {}
            v = _coerce_empty(v, subschema)
            out[k] = normalize(v, subschema)
        # add missing required
        for req in required:
            if req not in out:
                out[req] = normalize(None, props.get(req, {}))
        return out

    # 3. Array ---------------------------------------------------------------
    if schema_type == "array":
        if data is None:
            return []
        if not isinstance(data, list):
            data = [data]
        item_schema = schema.get("items", {})
        return [normalize(item, item_schema) for item in data]

    # 4. String --------------------------------------------------------------
    if schema_type == "string":
        if data is None or not isinstance(data, str) or data == "":
            pattern = schema.get("pattern", "")
            if "${{" in pattern:
                return "${{ PLACEHOLDER }}"
            if pattern:
                return "PLACEHOLDER"
            enum = schema.get("enum")
            if enum:
                return enum[0]
            const = schema.get("const")
            if const is not None:
                return const
            return ""
        return data

    # 5. Number / integer ----------------------------------------------------
    if schema_type in ("number", "integer"):
        if isinstance(data, (int, float)):
            return data
        return 0

    # 6. Boolean -------------------------------------------------------------
    if schema_type == "boolean":
        if isinstance(data, bool):
            return data
        return False

    # 7. Fallbacks -----------------------------------------------------------
    if isinstance(data, dict):
        return {k: normalize(v, {}) for k, v in data.items()}
    if isinstance(data, list):
        return [normalize(item, {}) for item in data]
    if isinstance(data, str):
        maybe = _parse_to_dict(data)
        if isinstance(maybe, dict):
            return maybe
    return "" if data is None else data
