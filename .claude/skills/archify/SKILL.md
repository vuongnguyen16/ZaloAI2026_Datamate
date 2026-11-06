---
name: archify
description: "Create validated architecture, workflow, sequence, data-flow, lifecycle/state, ERD, class, tree, timeline, and waterfall diagrams as explorable standalone HTML, or a one-page explainer. Inspect repository evidence for code-backed diagrams. Use when visualizing systems, API calls, pipelines, schemas, histories or timings, or when the user asks for a page/explainer to share. English or Vietnamese only. Not for dashboards."
---

# Archify (Claude Code entry point)

The Archify package is installed once for every agent at `.agents/skills/archify/`.
This file only registers it for Claude Code; do not copy the package here.

1. Read `.agents/skills/archify/SKILL.md` and follow it exactly.
2. Resolve every relative path in that file (`references/`, `schemas/`,
   `examples/`, `assets/`) against `.agents/skills/archify/`.
3. Replace `bin/archify.mjs` in every command with
   `.agents/skills/archify/bin/archify.mjs`, run from the repository root.
4. Keep outputs under `.archify/` (git-ignored) as that file describes.
