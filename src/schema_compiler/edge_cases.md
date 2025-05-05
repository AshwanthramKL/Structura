# Edge-case spec for `converter.py`

1. **Root metadata** — ignore `$schema`, `$id`, `$comment`.
2. **patternProperties** — fallback to `#json { ... } #` raw block.
3. **Conditional (`if/then/else`)** — flatten into `anyOf`.
4. **Enums > 50 items** — keep full list; insert comment `// large enum`.
5. **Numeric ranges** — emit `@min` / `@max` comments.
6. **Arrays** — add hidden `items_count int`.
7. **Descriptions** — preserve via `@description`.
8. **Unknown keywords** — comment `// TODO unsupported: <kw>`.
