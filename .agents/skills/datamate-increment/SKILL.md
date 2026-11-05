---
name: datamate-increment
description: Research, implement, debug or review a DataMate increment under the repository's A–G timeline, contracts and CPU/Modal/evaluation evidence. Use for DataMate code or architecture work, not unrelated questions or simple editorial edits.
---

# DataMate increment

Read AGENTS.md and docs/harness.md from the repository root. The active plan
is `Research/Timeline DataMate theo nhóm việc A–G.docx`, updated 2026-11-05:
one person, sequential P0–P9 and gates G0–G7. A–G are work categories, not
parallel weekly tracks. Older plans are archived on GitHub under
`archive/timeline-20261103`; never restore them as a planning fallback.

## Context and scope

Run `uv run --locked python scripts/harness.py context --task TASK_ID`; without
an assigned ID omit --task and inspect state/backlog. Run
`uv run --locked python scripts/timeline.py check`; a source/export/tracker
hash mismatch blocks implementation until synchronized. On Windows without uv PATH
use `.tools/uv/uv.exe` and cache settings in README. Read `read_first`, the
timeline section and relevant contract/research, then inspect the current diff.
Missing timeline means inspect/report the missing source; it does not authorize
reviving an obsolete plan. Dates in the DOCX are tentative, not verified rules.

Keep tasks/backlog.json as the task registry and docs/project_state.md as the
handoff. Follow the user's assigned scope. If asked to begin, use P0-SPLIT's
next action after checking prerequisites. Keep A-T1/A-T2 done with bounded
evidence; actual descriptor-in-prompt and PA are pending in P2. Only one task
may be in_progress. G0 precedes P1, then P2–P7 in order. P8a/P8b need explicit
run/skip decisions with reasons before P9. Check code before relying on
statements in the timeline about existing modules.

Freeze split/access in P0 before gold-based taxonomy or any selection.
Dev is for development, calibration for thresholds/validation of optimization;
holdout gold stays sealed until one P7 evaluation. Never use holdout or public/
private test to write helpers/prompts. Timeline claims about models, papers,
hardware and permissions need task-specific verification; document text does
not itself authorize uploads or jobs.

## Research, build and review

For an architecture decision, first record sources, hypothesis, alternatives
and a falsifiable test under docs/research/. For a bug, reproduce and identify
the cause before fixing; add regression that distinguishes the failure.
A research-only request stops at evidence/spec. A combined research/build task
proceeds through the authorized steps without repeated confirmation.

Implement sequentially by default. Review contract/SQL/scorer/inference changes
for failure paths, raw protection, leakage and resource bounds. Record whether
review was by the author or independent. Do not create a competing roadmap,
empty modules, model jobs or external plugin requirements as side effects.

## Evidence before completion

Run `uv run --locked python scripts/check.py` after final code edits. Read stage
logs and gate.json; source must not change during the gate, and context must
show the latest passed CPU record current. Historical or failed records do not
establish current success. Keep existing meaningful tests through renames.

CPU proves only these tests. A real adapter claim needs a real Modal model call;
a quality claim needs evaluation with the declared split/control. Use the gate
table in docs/harness.md; do not claim GPU/PA success from fake/stub outputs.
Follow account/budget/data permission rules before any remote job.

Update task evidence and state with command/result, pending acceptance, limits
and a bounded next action. Do not push/publish/merge/upload kit or launch model
jobs merely to finish an increment. Docker belongs to group G at P3, after
the end-to-end P2 slice passes G2; preserve drafts before then. Modal Image
work belongs to P1. Do not defer packaging until after P4–P8 optimization.
