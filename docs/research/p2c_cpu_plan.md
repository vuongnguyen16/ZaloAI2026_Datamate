# P2c CPU Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, inline trong workspace đã chọn.

**Goal:** Core CPU có thể kiểm cho revenue/order count, cùng sửa3minor probe.
**Architecture:** explicit raw bindings→ledger có lineage→resolver/filter→Decimal
metrics; tách khỏi model và scoped gold. Không tự suy binding thật.
**Tech Stack:** Python stdlib/Pydantic hiện hành; uv/lock không thêm dependency.
**Spec:** `docs/research/p2c_cpu_design.md`, `docs/research/p2c_domain_scope.md`.

## Global Constraints

- Chỉ P2 active; chưa model/full-dev/PA/G2 hoặc binding thật được nghiệm thu.
- Không đọc gold mới, không sửa data/split/scorer, local CPU synthetic nhẹ.
- Không bỏ unknown filter, suy status/date/amount, hard-code business/question ID.
- Source/raw/coordinate giữ nguyên, Decimal không float, giới hạn bộ nhớ/dòng.
- Throughput gate và short prompt ghi trước probe, chưa lấy số proposal làm kết quả.

## Review Focus

1. Return sau ngày neo vẫn loại đơn: test event trước period filter.
2. Dedupe/grain/join: test same-order identical rows, different IDs, repeated header.
3. Số/đơn vị/date sai: abstain, count vẫn độc lập money; test huge/float/missing.
4. Unknown/ambiguous filter và anonymous/line/order scope: không silent discard.
5. Prefix/phase diagnostics: test warmup failure checkpoint và snapshot stderr sanitize.

### Task 1: Minor probe và cảnh báo throughput
**Files:** intent_probe.py; context_generate.py; infra/context_probe_process.py;
modal_context_probe.py; tests/unit/test_context_probe_diagnostics.py.
**Interfaces:** `verify_context_snapshot(candidate,target,checkpoint)`;
Intent.filter_texts items<=256; checkpoint phase warming_up/ready.
- [ ] RED tests:257char filter rejected; warmup raises leaves init duration;
  failed snapshot writes bounded redacted stderr; image includes helper.
- [ ] Minimal fixes, report clarifies sample/non-causal/time limitations.
- [ ] Run targeted tests; Expected all pass; commit.

### Task 2: Resolver kỳ
**Files:** domain_lib/model.py, periods.py, __init__.py;
tests/unit/test_domain_periods.py.
**Interfaces:** `Period(start,end)`, `DomainAbstain(code)`,
`resolve_period(text,as_of)`, `previous_period(text,as_of)`.
- [ ] RED boundary fixtures:leap/year/quarter/month clamp/week Mon/N inclusive;
  malformed/multiple/unknown/Tet abstain; this-month comparison versus full explicit month.
- [ ] Implement strict full-match, CPU only, deterministic and bounded.
- [ ] Run resolver tests; Expected pass; commit.

### Task 3: Adapter, exact filters và metrics
**Files:** domain_lib/orders.py, metrics.py;
tests/unit/test_domain_orders.py, tests/integration/test_domain_metrics.py.
**Interfaces:** RawRow/Binding/BoundSource/Ledger/Filter; `adapt_sources(sources)`;
`revenue_total(ledger,period,filters=())`, `order_count(...)`.
- [ ] RED tests review focus1–4; no-filter and exact-filter answers, boundary0,
  no data !=0, role/status/date conflicts, no mutation, row cap.
- [ ] Implement explicit binding/validation, group/dedupe/lineage and Decimal sum;
  no CSV inference or receipts join. Unsupported source remains abstain.
- [ ] Run all domain tests and full CPU gate; Expected pass/current.
- [ ] One fresh independent source/synthetic review, fix Important by RED→GREEN;
  record limits, update state/backlog and commit. Probe/full dev remain next bounded action.
