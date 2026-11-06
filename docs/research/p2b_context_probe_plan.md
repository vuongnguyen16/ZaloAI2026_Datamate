# P2b context/throughput Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, triển khai inline theo thứ tự.

**Goal:** Đo BF16 context và batch1/2/4 trên câu dev + descriptor thật,
không gold và không PA.

**Architecture:** CPU tạo payload allowlist từ scoped dev và schema A-T2.
Modal tái dùng runtime/weights P1 read-only; mỗi context-config một process,
engine thường trú qua warmup và các batch. Dữ liệu/kết quả thật giữ local.

**Tech Stack:** Python/uv hiện hành; Pydantic; Modal; runtime GPU P1 đã khóa.

**Spec:** `docs/research/p2_intent_prompt_cache.md`,
`docs/research/p2c_domain_scope.md`.

## Global Constraints

- Model thật chỉ Modal; Qwen3-14B revision đã chọn, BF16/TP1,30GiB.
- Workspace vuonghungnguyen07; tối đa30USD/thí nghiệm, fresh billing<=24h.
- Chỉ dev question/context, không type gold/answer/alias hoặc calibration/holdout.
- Không sửa P1 config/schema hay split/access/scorer để chạy P2.
- Batch1/2/4 cùng4 prompt hợp lệ/context,2lượt; cache/prefix cache tắt.
- Chưa model throughput/PA pass trước khi đọc bằng chứng thật.

## Review Focus

1. Payload lẫn gold hoặc metadata sealed: allowlist strict và synthetic test.
2. Descriptor quá dài/cắt mất evidence: projection khai báo omission; oversized
   prompt bị loại nguyên vẹn, không truncate câu hỏi/JSON.
3. Sai account/credit/app trùng: preflight trước tạo transport và regression.
4. Một context OOM/deadline: checkpoint từng config; kill process group,
   không tự retry hoặc đổi model/dtype.
5. Giả throughput từ cache/khác workload: batch schedule cố định, token counts,
   duration; chỉ báo đo thực, không ngoại suy6giờ như acceptance P3.

### Task 1: Policy và payload CPU

**Files:** `src/datamate/intent_probe.py`, `tests/unit/test_intent_probe.py`.
**Interfaces:** `ContextProbeConfig` kế thừa policy P1 và chỉ mở context4096/8192;
`project_descriptor(schema) -> dict`, `make_case(question, descriptor) -> dict`,
`intent_schema() -> dict`, `validate_intent(text) -> dict`,
`batch_schedule(n, size) -> list[list[int]]`.

- [x] Test RED: config context không khóa2048, vẫn chặn budget>30;
  projection bỏ business/cache path/samples và báo omission;
  make_case từ chối keygold, schema strict, parser không repair;
  schedule4request cho batch1/2/4 không mất/trùng.
- [x] Implement đúng interface, không import model/cloud ở CPU.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/unit/test_intent_probe.py -q`;
  Expected: tất cả pass. Commit task1.

### Task 2: Transport, chuẩn bị dev và evidence

**Files:** `infra/modal_context_probe.py`, `infra/p1_runtime/context_generate.py`,
`scripts/p2_context_probe.py`, tests integration synthetic cho CLI guard/image.
**Consumes:** interface task1; P1 preflight/build_images/probe_process helpers.
**Produces:** local payload/provenance/events/result/summary; app/evidence key.

- [x] Test RED: bad billing/account không gọi factory; image chỉ allowlist code;
  inference payload chỉ `id/messages`, không gold; app inventory chặn P2 đang chạy.
- [x] Implement prepare/check/run tách biệt. Prepare chỉ scoped dev và descriptor
  từ profile index có provenance hash; verify source/schema hashes. Validate
  payload cả local và remote, finite bounded inputs. Chọn4 request/context
  theo độ dài prompt đo được, không theo gold/độ đúng output.
- [x] Worker offline/read-only/hash weights, max_num_seqs4, eager, cache tắt;
  checkpoint warmup/init/token/VRAM/log và2lượt batch. Giữ failure evidence.
- [x] Run tests task1+integration. Expected: pass, cloud factory fake trong CPU.
- [x] Full CPU gate + đọc JSON/log. Expected: passed/current. Review độc lập
  source/synthetic package; không gửi payload thật/gold cho reviewer.
- [x] Check account/apps/billing, sau đó một job tối đa1200s GPU, không retry.
  Expected: evidence thật hoặc failure có nguyên nhân, không giả pass.
- [x] Báo kết quả thực, cập nhật state/backlog. Commit task2.
