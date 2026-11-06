# P1 Modal Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Người dùng đã duyệt thiết kế và chọn triển khai trực tiếp trong workspace.

**Goal:** Implement and verify the approved P1 model/runtime smoke, then run
both eligible candidates sequentially only after live account/billing preflight.

**Architecture:** CPU-only policy, fixture and evidence code is separated from
lazy Modal orchestration and cloud-only vLLM worker. CPU staging commits a
hashed immutable model snapshot; GPU inference mounts it read-only/offline.

**Tech Stack:** Python3.11, uv/lock, Pydantic2, Modal, cloud vLLM0.11.1,
torch2.9.0/cu128. No local GPU dependencies or model weights.

**Spec:** `docs/research/p1_modal_design.md` (approved 06/11/2026).

**Execution:** Complete; P1/G1 done, P2 todo/ready. Evidence and final CPU
gate are recorded in `reports/p1_results.md`; state/backlog remain the tracker.

## Global Constraints

- During execution P1 is the only in_progress task; no P2/Docker implementation.
- Account/workspace vuonghungnguyen07; authorized ceiling30USD/experiment,
  no hard billing-cap claim. User confirmed at least30USD available before jobs.
- Model snapshot eligibility before2026-10-01; total<=15B, no auxiliaries.
- Only synthetic50 prompts; two fresh engine subprocesses, sequential,
  same GPU container/config; no BTC/gold/membership/public/private data.
- Inference read-only weights and block_network; measured peak<=30GiB,
  engine target29GiB after observed overhead, never a physical GPU partition.
- Local CPU only; GPU/staging dependencies lock separately and install cloud.

## Review Focus

Account/profile mismatch, stale billing, non-finite budgets or a floating
revision must stop before any SDK/App/Image/Volume side effect. Imported
code must not contact cloud. A path/hash mismatch must not silently fetch a
different snapshot. Missing/duplicate/malformed results, reused processes or
missing memory/offline telemetry cannot pass. Raw outputs must survive a
failed validation, and failed cloud runs must be preserved without retry.

### Task 1: CPU policy and eligible snapshot inventory

**Files:** `src/datamate/model_probe.py`, `configs/p1_probe.yaml`,
`manifests/models.json`, `tests/unit/test_model_probe.py`.

**Interfaces:** `ProbeConfig`, `ModelCandidate`, `preflight(config, model,
account, billing, now)->dict`, `verify_snapshot(directory, files)->dict`.
Preflight checks all policy values before transport is constructed.

- [x] Write tests for valid preflight plus account/budget/stale billing/
  revision/cutoff/aggregate/path/hash failures. Observe missing implementation.
- [x] Implement strict CPU-only models and guards; no SDK/GPU imports.
- [x] Populate candidates from official HF metadata only, verify all shard
  history/LFS hashes and exact parameter inventory. No weights download.
- [x] Run targeted tests and inspect results. Commit this deliverable.

### Task 2: Synthetic fixture and fail-closed acceptance

**Files:** `src/datamate/probe_fixtures.py`, `src/datamate/probe_results.py`,
`tests/unit/test_probe_results.py`.

**Interfaces:** `build_cases()->list[dict]` (50 self-contained cases with
local expected); `inference_cases(cases)->list[dict]` drops expected;
`evaluate_probe(cases, rounds, telemetry)->dict` preserves raw failures.

- [x] Tests cover50 unique IDs,9types, no expected in inference payload;
  50/50valid each round, normalized equality, per-type correctness,
  bad JSON/NaN/duplicate/missing ID, reuse PID and missing/offline/memory fail.
- [x] Observe RED, implement minimal fixture/evaluator, observe GREEN.
- [x] Run both task test files. Commit this deliverable.

### Task 3: Cloud staging, GPU worker and guarded entrypoint

**Files:** `infra/modal_model_probe.py`, `infra/p1_runtime/pyproject.toml`,
`infra/p1_runtime/uv.lock`, `infra/p1_runtime/generate.py`,
`scripts/p1_probe.py`, `tests/integration/test_model_probe.py`.

**Interfaces:** orchestrator lazily imported after CPU preflight;
`run_probe(config, model, preflight_record, cases, output_dir)->Path` creates
unique evidence before cloud launch. CPU stage returns hashes; GPU transport
returns two raw rounds + telemetry, worker loads only pinned local snapshot.

- [x] Write import/guard/failure evidence integration tests using fake transport;
  observe RED before implementation. No live cloud in tests/collection.
- [x] Resolve cloud lock for Linux/Python3.11 only; install nothing GPU local.
- [x] Implement metadata preparation, allowlisted uploads, CPU stage, read-only
  mount/block_network, two fresh subprocesses, bounded timeouts/retries,
  memory sampling, stdout/error and model/image/runtime identity evidence.
- [x] Test workers' pure helpers and orchestration failure paths without GPU;
  run all P1 tests and CPU gate. Commit deliverable.

### Task 4: Review, bounded live experiment and handoff

**Files:** `reports/p1_results.md`, `docs/modal_runbook.md`, state/backlog;
run artifacts remain ignored.

- [x] Fresh whole-branch review against spec/Review Focus. TDD fix material
  findings; preserve source/gate freshness after final changes.
- [x] Confirm live account and fresh user/dashboard billing evidence, OCI
  base digest, GPU price/cost estimate, no conflicting app; no auto retries.
- [x] Stage and probe each candidate once, inspect cloud logs/returned hashes,
  outputs/peak/offline/independent engines. Debug failures before another job.
- [x] Mark G1/P1 only from actual evidence; if external verification is
  unavailable, keep P1 in_progress and record precisely what remains.
- [x] Final CPU gate/log/context, state/backlog/report, local commit. No push
  or merge inferred from this implementation request.
