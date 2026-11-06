# P2a Review Fix Plan

Goal: fix PR1 review1–6 and merge only after fresh CPU/CI success.
Spec: docs/research/p2a_review_fixes.md. Inline execution, same authorized branch.

## Global Constraints

- One active P2; no cloud/model/gold or split/G5 changes.
- Preserve old finals and checkpoints; no identity mismatch resume.
- Source code/config/tests only on GitHub; taxonomy cells local/conversation only.

## Review Focus

- Existing logs directory and per-question contract logs on resume.
- Per-query timeout/error versus systemic startup/dead worker failure.
- Failsafe must not overwrite finals, bypass output guards, or decode gold.
- Exclusive fallback races and process death during non-atomic copy.
- Recursive code hash changes must invalidate old checkpoints.

### Task 1: Runtime fixes and regressions

Files: prediction.py, prediction_store.py, new prediction_failsafe.py, cli.py;
tests/integration/test_prediction.py, new test_prediction_review.py, store tests.
Interfaces: run_predict remains strict; submission_predict/run_failsafe protect CLI;
publish_chunks(..., allow_exclusive_fallback=False) enables explicit degraded mode.
- [x] Regression preexisting logs and q1 timeout/error followed by valid q2–q4; observe RED.
- [x] Move runtime state/logs and isolate transient failures; observe GREEN.
- [x] Regress config/import/identity/hardlink/input-budget failures and >10000 IDs,
  same/different/racing finals; observe RED then implement strict+failsafe separation.
- [x] Regress recursive code hash and unsupported link xb mode/race/permission errors.
- [x] Run prediction/store suites; expected all pass. Commit runtime fixes.

### Task 2: Documentation and tracker

Files: README.md, state/backlog/report/design.
- [x] Separate README commit describing predict and its degraded mode honestly.
- [x] Record source, tested scope, remaining limits and current P2 status before gate.
- [x] Check timeline and UTF-8/links/diff; expected current/no issues. Commit.

### Task 3: Review, gate, CI and authorized merge

Files: report/state; no raw/cells uploads.
- [x] One fresh source/synthetic-only reviewer for revised increment; material fixes TDD.
- [x] uv run --locked python scripts/check.py; read JSON/three logs; expected pass/current.
- [x] Push branch, ready PR, wait for exact-head CI success and inspect logs.
- [x] Merge PR with expected head, sync local main; keep evidence and report final.
