---
name: graphify
description: Navigate DataMate code relationships, symbols and call paths using its local Graphify AST graph. Use for architecture or cross-file questions; project state, timeline and evaluation policy still come from their source files.
---

Use the repo's CPU-only wrapper from the repository root:

```powershell
.venv/Scripts/python.exe scripts/graphify_local.py query "run_eval read_scoped" --budget 1200
.venv/Scripts/python.exe scripts/graphify_local.py explain "read_scoped"
.venv/Scripts/python.exe scripts/graphify_local.py path "run_eval" "score"
```

For a broad code question, query once with concrete symbol names, then read only
the returned source locations needed to answer or edit. Treat inferred edges as
navigation hints. Use rg for exact strings, missing symbols or insufficient graph
coverage. Avoid reading the full graph JSON or report into context.

Queries refuse missing/stale graphs. Run `scripts/graphify_local.py update` with
the same Python interpreter to refresh; `build` also works on first use. After
edits, update once when cross-file navigation is needed again. Reuse a current
graph across sessions. `status` prints freshness and counts; `html` exports the
optional local visualization.

Only src/scripts/tests/infra Python code is indexed. Backend is disabled and
queries are not logged globally. Do not use upstream `/graphify .`, semantic
extraction, cloud, raw gold or model extras to expand this setup. Documentation,
fixtures, BTC data and runs are outside its scope. Read required DataMate context
directly; the graph does not replace contracts, source inspection or CPU gates.

If the isolated tool environment is absent, run
`.tools/uv/uv.exe sync --project tools/graphify --locked` with the README cache
settings. Full setup and limits: [docs/graphify.md](../../../docs/graphify.md).
