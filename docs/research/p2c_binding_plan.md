# P2c binding CPU Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, inline workspace hiện hành.

**Goal:** Reader verified + rule candidates + audit18dev, có packet duyệt local.
**Architecture:** A-T1/A-T2 evidence→read-only streaming→semantic column rules→
format/status/data checks→ledger per metric; không tự duyệt thành oracle.
**Tech Stack:** Python/DuckDB/uv hiện hành, không thêm dependency/model.
**Spec:** `docs/research/p2c_binding_design.md`.

## Global Constraints

- Chỉ P2 active; chỉ dev context, không gold mới/model/cloud/full-dev PA.
- Raw read-only, source/cache/profile hashes và source unchanged trước/sau.
- Binding rule không hardcode business/question ID; BTC packet chỉ local.
- Count/revenue gates tách, unknown label/format/row không silently discard.
-95% arithmetic là diagnostic screen, không thay semantic evidence.
- Hai lượt review source/synthetic theo yêu cầu người dùng; không gửi kit/gold.

## Review Focus

1. Forged/stale schema/database/source: reader fail before yielding rows.
2. Total/repeated-header/continuation rows: retain lineage, no last-order pollution.
3. Net/gross ambiguity and equivalent numeric grammars: abstain rather than price-scale guess.
4. Unknown statuses/return sources/sheet coverage: whole count gate fails safely.
5. Resource timeout/row caps/memory: never publish a truncated ledger as checked.

### Task 1: Verified reader và explicit codecs
**Files:** domain_lib/raw_reader.py; orders.py; tests/integration/test_raw_reader.py;
tests/unit/test_binding_codecs.py.
**Interfaces:** `VerifiedBusiness`, `open_business(index,source,business_id)`;
`iter_rows(unit)` yields full RawRow; explicit en/vi-text-date codec in Binding.
- [x] RED synthetic source+cache+profile fixture: correct rows, invalid hash/view/
  source mutation rejected, repeated header/totals accounted, full cells preserved.
- [x] RED codec/grouped-comma/vi-text date tests, no permissive week/date guessing.
- [x] Implement minimal generic reader, read-only safe SQL identifiers, bounded batches.
- [x] Run targeted tests; Expected pass; commit.

### Task 2: Rule binder, audit và local review packet
**Files:** domain_lib/binding_rules.py, binding_audit.py; scripts/p2_binding_audit.py;
unit/integration synthetic tests for semantic/machine gates and CLI scope.
**Consumes:** reader task1/Binding/ledger CPU.
**Produces:** per-business candidate/check/reason/capability/provenance/resource
artifact and review packet local; aggregate result report.
- [x] RED false-net despite perfect arithmetic; grammar ambiguity; unknown status;
  row/resource/sheet gap and sealed CLI scope; count independent of money.
- [x] Implement exact README/header rules, full inventories/data checks, serialized
  worker time/RSS; research CLI authorize all18dev context before reading.
- [x] Run synthetic tests/full CPU gate; Expected pass/current; review source round1.
- [x] Run18business CPU, measure largest, inspect candidate bindings as author;
  write local packet, no independent/oracle claim. Report actual failures.
- [x] Review round2 source/synthetic+aggregate only per explicit user request,
  fix important RED→GREEN, final gate/current; update state/backlog, commit.
