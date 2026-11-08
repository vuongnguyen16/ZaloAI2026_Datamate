# P2c structural binding Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans in the current workspace, feature branch; implement sequentially. User authorized implementation on08/11/2026.

**Goal:** Diagnose dev source blockers per metric and connect repeated, supported structures to the verified ledger without guessing semantics.
**Architecture:** Verified dev reader → local source diagnosis and repeated-pattern evidence → bounded structural binder → independent count/revenue checks. Unresolved semantics become proposal/review work, not implicit capabilities.
**Tech Stack:** Existing Python/DuckDB/uv; no new dependency.
**Spec:** `docs/research/p2c_binding_design.md` (08/11 addendum), `docs/research/p2c_cpu_design.md`.

## Global Constraints

- Only P2 active. Dev context only; no new gold, calibration, public/private tuning or model calls as a side effect.
- Raw/cache/profile/split remain immutable; preserve provenance checks and old evidence.
- New binder capabilities require the same structural pattern in>=2dev businesses; report cluster count separately.
- Classify blockers(a) core-supported,(b) repeated new structure,(c) semantic, per business/metric; allow multiple blockers.
- After the bounded header/detail/event round, no second cluster checked means stop adding rules and record remaining LLM proposal work.
- CPU-checked, author-checked, independently approved and PA remain separate claims.
- Current CPU gate fails kill/resume timeout; reproduce and instrument before any fix. Do not loosen expected results.

## Review Focus

1. A master/receipt/return source misclassified as irrelevant: require positive semantic scope evidence, never missing-date/no-key exclusion.
2. Header/detail joins multiply or lose orders: unique header values, no orphan detail/event, complete source accounting.
3. Money/event ambiguity blocks only the metrics it actually affects, without silently dropping unknown statuses.
4. Diagnostics must not make a candidate into an approved capability, or skip later blockers after an early failure.
5. Real-data packets stay local; source/synthetic review receives no BTC membership, rows or gold.

### Task1: Baseline and local diagnosis

**Files:** new `domain_lib/binding_diagnostics.py`, `scripts/p2_binding_diagnose.py`, synthetic unit/integration tests; local evidence under runs.
**Interfaces:** diagnosis consumes verified schema/README and audit checks; returns per-unit hypotheses/evidence and per-metric blockers, plus pattern occurrence counts by distinct business/cluster.
- [x] Reproduce kill/resume with original assertions; preserve observations, instrument only if needed.
- [x] Inspect18authorized dev source structures locally to identify repeated patterns before changing binder.
- [x] RED tests: simultaneous structural/semantic blockers retained; metric isolation; duplicates within one business never count as repeated across businesses; nondev denied before read/output.
- [x] Implement diagnostics and dev-only CLI, collect local per-business evidence and publish only aggregate counts.

### Task2: Bounded structural binder round

**Files:** `binding_rules.py`, `binding_audit.py`, focused source-role helper if needed; synthetic binder integration tests.
**Consumes:** verified reader/core and Task1 pattern evidence.
**Produces:** explicit validated header/detail/event bindings for eligible repeated structures; metric checks and unresolved reasons.
- [x] Select only repeated(a)/(b) patterns proven by Task1; record source hypothesis/alternatives/falsifiable checks in design before code.
- [x] RED cases: valid header/detail; orphan/conflicting or duplicate header; partial/future event semantics; ambiguous source/status/net; count independent from money.
- [x] Implement minimum binder changes; preserve every existing protection and test.
- [x] Run targeted regressions, then new18dev audit with fresh output; compare machine-check results by metric/cluster and apply stop rule.

### Task3: Review and handoff

**Files:** result report, state/backlog; no competing tracker.
- [x] Review source/synthetic for leakage, completeness, semantic uncertainty, failures and resource bounds; fresh reviewer gets only source/synthetic instructions.
- [x] Fix Important findings with RED→GREEN; update tracker evidence/next action before final fingerprint.
- [x] Run locked `scripts/check.py`; inspect gate.json/all stage logs and context freshness. Report actual CPU/model/PA separately.
- [x] Verify UTF-8/NFC, timeline sync, publication diff and local-only artifacts; leave reviewable branch without push/merge.

### Task4: Bounded semantic proposal probe after stop rule

**Files:** `src/datamate/binding_proposals.py`, `scripts/p2_binding_proposals.py`, `infra/modal_binding_proposals.py`, `infra/p1_runtime/binding_generate.py`, synthetic proposal/preflight tests.
**Consumes:** verified dev reader, existing pinned model/runtime/preflight; fresh user-confirmed credit08/11>=30USD.
**Produces:** at most16metadata/status proposal cases, content-addressed outputs with exact citation/column checks, never automatic binding approval.
- [x] RED schema/citation/unknown/foreign-column/cache identity and scope/transport-boundary tests.
- [x] Prepare deterministic bounded dev projection: up to2business/cluster, one unresolved source plus one sampled raw status case each; no gold/question IDs/row samples in cloud.
- [x] Cache key binds payload+code+model revision+rulebook; run rebuilds authorized payload and checks fresh billing/live account before transport. SDK retries0; one corrected verification after diagnosed pre-model dependency failure as ruled below. BF16/4096<=30GiB, read-only weights/network blocked, no local weights/GPU.
- [x] Verify CPU/source review before job; record real outputs, truncated/invalid quotes as failures, total memory/duration and actual billing unknown separately. This is semantic-proposal evidence, not question-intent throughput or PA.
- [x] Apply final source-only review/CPU gate and update handoff, leaving production integration and any required business approval explicit.

## Execution ledger

- Ruling: reuse `scripts/p2_binding_audit.py` dev authorization/worker machinery with diagnose modes instead of a duplicate CLI; reduces divergence at the access boundary.
- TDD: six structural integration cases failed on the original binder after fixing fixture artifact layout and using fingerprint-bound header annotations;25targeted structural/diagnostic/legacy tests then passed12.99s. Initial fixture/setup errors are not counted as feature RED evidence.

- Ruling: use existing workspace on `work/p2c-structural-binding`, preserving two approved documentation edits; avoids duplicating large local-only input/cache and matches prior inline execution preference.
- Baseline: original kill/resume test passed once in21.20s with no code change; prior35s resume timeout remains unexplained, not declared fixed. Pytest default cache denied; subsequent runs use explicit ignored cache under runs.
- Pre-flight: Task2 consumes Task1 distinct-business pattern evidence; diagnostics report hypotheses only, never change source disposition or grant capabilities.
- Ruling: execute approved design continuously without another approval round; no model job without fresh account/budget verification.
- Ruling: first bounded rule audit remained1/18/one cluster; stop adding rule capabilities. User confirmed current credit>=30USD08/11, so prepare a small semantic-proposal probe under the already-approved two-tier architecture, not full1895dev model inference.
- Ruling: first cloud attempt ap-xWPWXkNx9WRQjrAqD72Ikc failed before model/snapshot because outer Python imported pydantic through diagnostic helper. Preserve failure; reproduce with Python-S; extract stdlib-only sanitizer and include it in both locked images. One explicit corrected verification attempt after fresh CPU/review/account check, SDK retries0; conservative combined reservation20USD remains below the experiment ceiling30USD, actual billing unknown. This is not a blind replay of the failed revision.
- Ruling: conversion recognition initially had a false-negative for registered annotated product definitions; explicit per-column label-role compatibility fixes this intended capability while still vetoing order/date/status/net conflicts. Synthetic RED→GREEN; no additional rule family selected after stop.

- Completion evidence: final structural audit18dev remains1/18/one cluster; stop rule enforced. Corrected Modal app completed13generations with8valid unknown/5reject,0accepted mappings;29.8389GiB/offline/read-only/cleanup pass. Local packet ready. Full CPU after tracker549passed/2skipped131.01s, source unchanged, context passed/current. This closes the bounded implementation/probe increment, not P2/G2.
