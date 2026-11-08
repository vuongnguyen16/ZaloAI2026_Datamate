# P2c reviewed semantics Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline in the current feature branch. User requested assessment and implementation08/11; human semantic decisions remain a final explicit gate.

**Goal:** Make observed blockers and dev semantic review actionable, fix proposal input/schema, without self-approving mappings.
**Architecture:** Scoped dev reader → inventory/review artifacts → SHA-verified human lexicon; independent source-span projection and per-case decoder. Audit/PA stay separate from review status.
**Tech Stack:** Existing Python/DuckDB/Pydantic/uv; no dependency changes.
**Spec:** `docs/research/p2c_reviewed_semantics_design.md`.

## Global constraints

- P2 active only; G2/split/scorer unchanged, P3 after G2.
- Dev only; no gold, calibration/holdout label inventory, cloud/model calls or BTC publication.
- Local read-only inputs/cache; packets stay ignored. Pending is never approved.
- Local CPU2threads/DuckDB256MiB, bounded streaming, resource measurement not permission to allocate512GB.

## Review focus

1. Wrapper/early/terminal failure falsely advertised as unlocked by one semantic change.
2. Pending/stale/conflicting lexicon accidentally changes runtime status meaning.
3. Missing README or rulebook span silently replaced by guessed prefix/alias.
4. Citation crosses disjoint excerpts; decoder permits duplicate column claims or non-ledger overbinding.
5. Reviewer/source packet exposes BTC artifacts or source roles are accepted without human approval.

### Task1: Observed blocker sets and inspection completeness
**Files:** `binding_diagnostics.py`, `binding_audit.py`, `scripts/p2_binding_audit.py`, synthetic tests.
**Interface:** per-metric blocker families + potential-only counterfactual and explicit uninspected units/ledger validation.
- [ ] RED status-only/source-only/both/other and wrapper-only/incomplete scan cases.
- [ ] Implement conservative grouping and aggregate distinct business/cluster counts; preserve existing flags/guards.
- [ ] Compute local report from dev audit; do not change checked flags to simulate success.

### Task2: Dev inventory and human review boundary
**Files:** `domain_lib/semantic_review.py`, `scripts/p2_semantic_review.py`, `binding_rules.py`, `binding_audit.py`, audit CLI; synthetic tests.
**Interface:** streaming inventory + pending lexicon/source packet; approved lexicon loader SHA/rulebook/receipt; optional explicit audit lexicon.
- [ ] RED pending/stale hash/conflicting base map/unseen labels/nondev scope cases.
- [ ] Inventory all verified order-status sources on18dev, record incomplete/omitted metadata; include full rulebook/README locators and peak RSS/time.
- [ ] Prepare candidate labels and source decisions local for user approval; never manufacture approval.
- [ ] Wire approved generic map into data checks; pending artifact must fail before reading audit data. Re-audit only after actual user approval.

### Task3: Source-span projection and per-case decoder
**Files:** `proposal_evidence.py`, `binding_proposals.py`, proposal CLI/runtime/transport; synthetic tests.
**Interface:** evidence spans with locators/hash/omission; source/table/partition resolver; per-case JSON schema; output512 config.
- [ ] RED late status clause, unrelated prefix, exact/partition/unmatched README, crossing-span citation, duplicate-column object and role-only cases.
- [ ] Implement selectors and schema; maintain old list replay but generate only column-keyed object.
- [ ] Prepare dev payload CPU-only with explicit omissions; validate no arbitrary truncation. No model repeat until review gates.

### Task4: Review, resource evidence and handoff
- [ ] Read relevant largest-business inventory/probe stats; retain guards until ledger measured with approved binding.
- [ ] Fresh source/synthetic reviewer only, fix Important with RED→GREEN; no real packet to agent.
- [ ] Update state/backlog/report, run full locked CPU, read JSON/logs/current context, UTF-8/NFC and timeline checks.
- [ ] Deliver concrete local approval packet; name pending steps (human approval, oracle control, model/PA/throughput), no G2 claim.

## Ledger

- Ruling: continue feature workspace from6695379, current branch, no main mutation; no new integration/publication requested for real data artifacts.
- Ruling: interpret '38 labels' as historical ceiling, inventory current authorized dev only; inventory/semantic-review artifacts cannot expand access policy.
- Ruling: grouping is observational potential, never a claim that removing one recorded reason passes later unexecuted checks.
- Ruling: complete all independent CPU/projection work before asking human approval; oracle mapping and actual re-audit with new lexicon depend on that approval.
- Task1: complete — observed status/source/joint/remainder groups and explicit inspection; synthetic RED→GREEN. Fresh default audit still1/18/one cluster; no new approved mapping.
- Task2: complete independent implementation — inventory18dev/29labels/212source units; all pending. Loader/CLI reject pending/stale/conflicting maps before auditor. Human approval/re-audit/oracle runtime intentionally pending.
- Task3: complete CPU implementation — clause/file/table/declared-partition projection, raw README SHA, single-span citations, case schema/output512; legacy list validation retained. GPU decoder compatibility/quality still unmeasured.
- Final review: three Important evidence issues plus remainder bucket regraded Important (otherwise blocked-business totals incomplete). Five synthetic failing regressions reproduced them; one fix pass40targeted tests green. No deferred minor.
- Final: Ruling: reviewer declined actual semantics/receipts, real-data/resource/PA, GPU decoder/throughput and packet publication assessment — human approval, actual CPU artifact checks and separately gated Modal remain distinct. No packet publication. Cost if wrong: delayed coverage or model runtime failure, never an inferred G2 pass.
- Final: fixed SQLite source association, original README digest, shared source-rulebook packet evidence and remainder bucket — regression RED→GREEN; full suite result recorded in results report.
- Task4: complete independent CPU handoff — packet v3 verified pending, payload16cases prepared CPU-only (2missing evidence flagged,16omissions disclosed), resource scope explicitly streaming only. Full locked CPU574passed/2skipped158.76s, Ruff/format pass, source unchanged; gate/3logs read. No human receipt/model/PA/G2 claim.
- Ruling costs: staying on the existing review branch keeps one PR larger; dev-only inventory may miss unseen labels; observational grouping can understate later blockers; human approval delays oracle/model work but prevents unsupported activation. These are explicit limits, not reasons to weaken access or acceptance.
- Follow-up08/11: user approved the29label Proposed group column and retained unknown; verified reviewed draft SHA, materialized23approved/6unknown entries in a new ignored artifact, loaded by explicit SHA. Source packet remained byte-identical and pending.
- Follow-up audit complete18dev: count/revenue still1/18/one cluster, no regression; unknown_status13→10. Observed count source-only now3business/2clusters; priority packet23unresolved units with27context units prepared locally. Source-role/oracle/model/PA/G2 remain gated; no new runtime code or semantic expansion.
- Follow-up verification: full locked CPU574passed/2skipped123.80s, Ruff/format pass, unchanged source; gate/3logs read, harness P2 passed/current, timeline/UTF-8/NFC/diff checks pass. Profile-index unchanged from18dev inventory; successful ledger provenance matches baseline. No model/gold/PA or approved source-role claim.
