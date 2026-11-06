# P2a Runtime Isolation Implementation Plan

> REQUIRED SUB-SKILL: superpowers:executing-plans, inline in current branch.

Goal: deliver a small PR fixing unrelated output entries and permanent timeout poisoning.
Spec: docs/research/p2a_runtime_isolation.md.
Architecture: shared owned-path admission, names-only diagnostics, explicit fatal backend statuses.
Stack: existing Python/stdlib/Pydantic/DuckDB; no dependencies or GPU work.

## Global Constraints

- Only P2 in_progress; runtime increment finishes before CPU surveys start.
- Preserve writer lock, owned-path guards, no-overwrite and private checkpoint admission.
- No Gold/kit/model/cloud access in runtime implementation/review/tests.

## Review Focus

- Unknown output symlinks must not be followed; owned logs/final must stay guarded.
- Unknown names must appear in both normal and failsafe diagnostics without contents.
- Any number of question-local failures must allow later healthy questions to run.
- Backend death/startup/protocol failures and global budgets must remain protective.

### Task 1: Runtime regressions and minimal fixes

Files: runtime_paths.py, prediction.py, prediction_failsafe.py;
tests/integration/test_prediction.py, test_prediction_review.py, new runtime regression file.
Interfaces: ignored_output_entries(output)->list[str]; output_layout remains Path-returning.
- [ ] Add lost+found/preserved-file/no-read and three-timeout/error regressions; observe RED.
- [ ] Remove count-based backend disable; restrict admission to owned paths and log ignored names.
- [ ] Update previous foreign-output assertions to the newly requested semantics; preserve guard tests.
- [ ] Run prediction/store/worker tests; expected pass. Commit.

### Task 2: Review, gate and PR

Files: state/backlog/report/README and ignored evidence.
- [ ] Source-only independent review once; Important/Critical fixes RED→GREEN if any.
- [ ] Record commands/scope, freeze tracker, run check.py; read JSON/three logs and current context.
- [ ] Timeline/UTF-8/links current; push only this branch and open small PR, inspect exact-head CI.
- [ ] Runtime increment done before starting the three CPU surveys and P2c scope note.
