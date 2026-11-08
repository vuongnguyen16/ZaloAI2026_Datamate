# Approved source exclusions Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; one fresh source/synthetic reviewer at the end. User approved exact six-source semantic scope; do not re-ask it.

**Goal:** Apply only approved default-unfiltered source exclusions, preserving all data gates.
**Architecture:** SHA-pinned receipt loader → verified-business identity matcher → audit effective source list → unchanged ledger gates. Explicit CLI opt-in and complete provenance.
**Tech Stack:** Existing Python/Pydantic/uv, no dependencies or model.
**Spec:** `docs/research/p2c_source_exclusions_design.md`.

## Global constraints
- Current feature workspace `work/p2c-count-feasibility` from e7e1c6c, PR8 draft; no main mutation or new task.
- Dev only, no gold/model/cloud/weights, no real packet in Git/reviewer.
- Approved6source exclusions only, both metrics/default-unfiltered; other17sources/6unknown unchanged.
- Row200000/identity128MiB/DuckDB256MiB/2threads unchanged. Source proof stale => fail.
- Internal per-function15answered/cluster/precision90%/2clusters and G2/split/scorer unchanged.

## Review focus
1. Same unit ID reused across businesses leaks an exclusion without matching proof.
2. Changed raw/schema/README/profile or missing approved unit silently reused.
3. Receipt disables order/event, unapproved source, status, cardinality or resource veto.
4. Scope/filter/metric expansion through CLI/helper or child flag mismatch.
5. Reviewed sources falsely counted as physical row scan or independent full-binding approval.

### Task 1: Receipt and matcher
Files: create `src/datamate/domain_lib/source_exclusions.py`, synthetic unit tests.
- [x] RED valid/pending/hash/time/duplicate/nondev/scope/metrics; identity match/missing/raw/profile/cross-business, known order/event and filtered veto.
- [x] Strict bounded loader, canonical unit digest and unresolved-only matcher; no raw access in loader.
- [x] GREEN targeted tests; ledger evidence below.

### Task 2: Audit/CLI integration
Files: binding_audit.py, scripts/p2_binding_audit.py, integration tests.
- [x] RED default source remains blocked; explicit receipt unlocks auxiliary source; another unknown source/status/resource stays blocked. CLI pending/missing pair/diagnose denied before output/auditor.
- [x] Wire effective sources plus traceable exclusions and required scan flag. Both metrics only, no filter capability.
- [x] Forward receipt to children, include SHA in evidence; GREEN targeted suite.

### Task 3: Real CPU evidence and review
- [x] Materialize approved artifact from exact packet SHA through verified dev reader, preserve drafts/lexicon; audit18dev and compare per metric.
- [x] One fresh-context reviewer: source/synthetic only, fix Important with RED→GREEN in one pass; no real packet read.
- [x] Update report/state/backlog, final locked CPU/gate/3logs, harness current, timeline and UTF-8/NFC/diff checks. Source/test/aggregate docs only in PR8, no merge.

## Ledger
- Pre-flight: Task1 matcher consumes source/proof produced by verified reader and feeds Task2 exclusions; allowlist scope fixed to both metrics so no partial ledger is presented as jointly valid.
- Ruling: use existing review branch/PR8 rather than new worktree — isolated feature workspace already active and owned by current increment; cost: draft grows beyond feasibility notes.
- Ruling: refuse subset-metric receipts in this increment — user approved the same six exclusions for both default metrics; cost: future asymmetric source relevance needs a separate design.
- Ruling: retain physical unscanned units and add required scan flag — count/revenue may pass with reviewed non-ledger sources unscanned; cost: older summaries remain conservative about physical scan completeness.
- Task1 complete: missing-module RED→GREEN21unit tests. Task2 complete:8integration failures RED→GREEN,55targeted tests passed19.60s; lint/format pass. Exact reviewed packet verified and6-source receipt compiled through verified reader; no other semantics changed.
- Final review: source/synthetic-only fresh reviewer,45tests passed11.80s, no Critical/Important. One minor deferred: positive CLI worker/child-forwarding synthetic regression coverage; current forwarding correct by inspection and real18worker SHA verification required below. No second review or unrelated fix pass.
- Final: Ruling: real receipt membership/results/other-source preservation, local human authenticity and full binding/PA/G2 were outside agent review — executor checks authorized real artifacts and gate; receipt remains local trust, not digital identity proof; cost if wrong is semantic or generalization uncertainty, not a claimed PA pass.
- Task3 complete: exact6source receipt applied18dev; count1→3businesses/1→2clusters(C3,C4), revenue1/18, no regressions. All18worker SHA pinned, only6coverage dispositions changed; other17sources/6unknown unchanged. Required source scan complete on2new ledgers; physical scan deliberately reports exclusions unscanned. Review no blocking findings; one minor deferred.
- Final verification: full locked CPU603passed/2skipped109.67s, lint/format pass, unchanged source; gate/3logs read, harness P2 passed/current, timeline/UTF-8/NFC/diff checks pass. Raw/receipt/packets remain local; no PA/model/G2 or integration claim.
