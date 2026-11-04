---
name: datamate-increment
description: Research, implement, debug or review a DataMate increment under the repository's A–G timeline, contracts and CPU/Modal/evaluation evidence. Use for DataMate code or architecture work, not unrelated questions or simple editorial edits.
---

# DataMate increment

Read AGENTS.md and docs/harness.md from the repository root. The active plan
is `Research/Timeline DataMate theo nhóm việc A–G.docx`. Older plans were
explicitly superseded; never restore them or consult Git as a planning fallback.

## Context and scope

Run `uv run --locked python scripts/harness.py context --task TASK_ID`; without
an assigned ID omit --task and inspect state/backlog. On Windows without uv PATH
use `.tools/uv/uv.exe` and cache settings in README. Read `read_first`, the
timeline section and relevant contract/research, then inspect the current diff.
Missing timeline means inspect/report the missing source; it does not authorize
reviving an obsolete plan. Dates in the DOCX are tentative, not verified rules.

Keep tasks/backlog.json as the task registry and docs/project_state.md as the
handoff. Follow the user's assigned scope. If asked to begin, use A-T1's next
action after checking prerequisites. Inherited foundations do not mean the
whole A/T1, E/T1 or G/T1 deliverables are done. Check code before relying on
statements in the timeline such as scorer already existing.

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
jobs merely to finish an increment. Keep Docker at group G packaging after the
pipeline is complete; preserve its existing drafts.
