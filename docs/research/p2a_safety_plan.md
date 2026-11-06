# P2a Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> User explicitly requested immediate inline execution of the revised spec.

**Goal:** Deliver CPU safety prediction and an authorized dev taxonomy cross-table.

**Architecture:** Exact Decimal JSON feeds immutable no-clobber artifacts and
append-only journal segments. A bounded prediction coordinator and isolated
DuckDB worker fail to abstain. Cross-table reads only the pinned P0 dev artifact.

**Tech Stack:** Python3.11/stdlib, Pydantic2, existing DuckDB; uv/lock unchanged.

**Spec:** `docs/research/p2a_safety_design.md`.

## Global Constraints

- One active tracker task P2; no Modal/model/PA/G2 claim or source-data mutation.
- Preserve old tests, smoke/stub, scorer policy, split lock/access and G5 rules.
- Local CPU only, no new GPU dependency, no arbitrary gold/metadata input.
- Windows reports unavailable directory fsync; P3 must check actual Linux mount.

## Review Focus

- Existing/racing final file must survive even when different or linked.
- Killed writer/torn segment/repeated ID cannot silently choose a conflicting answer.
- Startup/backend/query timeout must clean children and preserve remaining valid IDs.
- Decimal precision must survive the final bytes, not only an in-memory value.
- Taxonomy metadata cannot be an alternate raw-gold decode path or leak sealed IDs.

### Task 1: Exact numeric submission and serialization

**Files:** contracts.py, new serialization.py, legacy runner.py writer, tests/unit/test_serialization.py.
**Interfaces:** `submission_bytes(Submission|dict)->bytes`, `format_submission(id,type,answer,reason=None)->Submission`.
- [x] Write round-trip9type/Decimal1.0000000000000001/large-int/percent/negative-zero/reject tests; run and observe RED.
- [x] Implement bounded Decimal-compatible Submission and exact serializer; validate exact final line via scorer parse/validate, no score/gold IO.
- [x] Run new tests plus existing contract/scorer tests; expected all pass. Commit.

### Task 2: Immutable publication and checkpoint segments

**Files:** new prediction_store.py, tests/unit/test_prediction_store.py.
**Interfaces:** `publish(path,data)->dict`, `RunStore(output,identity)` context with `append(record)`, `recover()->dict`, no-clobber finalization.
- [x] Tests for existing same/different, injected race, unsupported hardlink, torn/full corrupt lines, same/conflicting duplicate and writer lock; observe RED.
- [x] Implement file fsync/link publication, platform capability, immutable manifest/segments, OS lock and bounded recovery.
- [x] Run store tests; expected all pass, old bytes unchanged. Commit.

### Task 3: Deadline and isolated trusted DuckDB worker

**Files:** new bounded_execution.py, tests/unit/test_bounded_execution.py.
**Interfaces:** `Deadline(started,budget,reserve)`, `run_duckdb(database,sql,parameters,timeout_seconds)->dict`.
- [x] Tests actual query/Decimal result, external-access rejection, bounded output, timeout interrupt/cleanup and forced terminate; observe RED.
- [x] Implement spawn worker with interrupt control thread, read-only/external-disabled/2threads/256MB and parent join/terminate/kill.
- [x] Run worker tests; expected pass and no live child. Commit.

### Task 4: Tolerant prediction coordinator and CLI

**Files:** new prediction.py, cli.py, configs/predict.yaml, predict.sh, tests/integration/test_prediction.py.
**Interfaces:** `read_prediction_questions(path)->(questions,rejected,errors)`, `run_predict(input,output,config,backend=None,started=None)->dict`; backend callable returns per-question result, default safe_abstain.
- [x] Tests mixed invalid/duplicate input, unchanged raw/gold sentinel, startup/backend failure, expired deadline, resume/mismatch/final conflict, CLI and real kill/resume; observe RED.
- [x] Implement input inventory/identity, bounded batches, checkpoint every ID, exact one-line output/log and diagnostics; CLI starts clock before loading and explicitly labels no_model.
- [x] Run integration/store/worker/numeric tests; expected pass; stub unchanged. Commit.

### Task 5: Authorized taxonomy cross-table and real aggregate

**Files:** new taxonomy_cross.py, cli.py, tests/integration/test_taxonomy_cross.py.
**Interfaces:** `cross_table(records)->dict`, `run_taxonomy_cross(split,manifest_sha256,output,proof=None)->dict`; supported CLI uses committed P0 proof only.
- [x] Tests hand-derived Cartesian counts, duplicate/out-of-scope IDs, proof/hash/source mismatch and no gold open; observe RED.
- [x] Implement pinned-before-decode artifact reader and dev authorization, no arbitrary CLI artifact path. Produce local aggregate/cell report, no record IDs/answers.
- [x] Run synthetic tests then real pinned dev artifact cross; inspect only aggregate summary, record path/hash, no sealed decode. Commit.

### Task 6: Whole-branch review and handoff

**Files:** report/state/backlog, run artifacts ignored.
- [x] Dispatch fresh source-only reviewer for this increment; fix Important/Critical with RED→GREEN.
- [x] Run `uv run --locked python scripts/check.py`, read gate/three logs and contextP2 current; timeline current.
- [x] Record real commands, platform limitations, local taxonomy provenance and pending P2b/c/G2; commit, no inferred push/merge.
