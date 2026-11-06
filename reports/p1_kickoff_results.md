# Khởi động P1 — 06/11/2026

Đây là báo cáo kickoff lịch sử. P1/G1 sau đó đã hoàn tất;
trạng thái và nghiệm thu cuối ở [kết quả P1](p1_results.md), state/backlog.

**P1 in_progress, G1 chưa đạt.** Đã sửa format, kiểm nền CPU và chuẩn bị
[thiết kế model probe](../docs/research/p1_modal_design.md) chờ người dùng duyệt.
Chưa có model adapter mới, chưa mở job GPU, chưa tạo Volume/tải weights.

## Đồng bộ và sửa lỗi có bằng chứng

Fast-forward local từ `f066cc5` tới `7371bf6a249061a8020662b404c43cf16b8fabd2`.
CI remote của commit này fail tại Ruff format trong hai file ingest; lint pass,
pytest chưa chạy. Đã tái hiện bằng:

```powershell
.venv/Scripts/python.exe -m ruff format --check src/datamate/ingest/loader.py src/datamate/ingest/model.py
```

Lệnh trước sửa exit1, đúng 2 file cần format; sau chạy formatter, check exit0.
Không sửa expected, bỏ test hoặc đổi hành vi. So AST thực thi trước/sau bỏ
docstring/attributes xác nhận tương đương; proof script local `.tmp/p1_kickoff.py`.
Đây là sửa local; chưa commit/push, không tuyên bố CI remote đã xanh trở lại.

## Context và kiểm tra

- Đã đọc README/state/backlog, harness, contract, split/provenance pointer,
  timeline P1/D1/G2 và Modal runbook. Không mở data/gold/artifact BTC.
- Timeline check current, DOCX hash không đổi:
  `b70f5e852b156c7ff0835eebbdd96ccb71b718fd095fd797b554efe5b1837219`.
- Graphify stale sau commit docstring; đã update và query phạm vi cpu_smoke/
  config, đọc source liên quan. Graph là local/ignored, không bằng chứng G1.
- Backlog chỉ mở P1; A-T1/A-T2/P0/G0 done giữ nguyên, P2 vẫn chưa ready.
- CPU: `uv run --locked python scripts/check.py`, exit0;
  **238 passed in 71.13s**, Ruff lint/format pass, source không đổi trong gate.
  Đã đọc JSON và đủ ba log ở
  `runs/cpu-check-20261106T063559581002Z-usdkdlqq/`.
- Context P1: dependency ready, latest CPU passed/current, không warning hoặc
  planning error; đúng một task active. `git diff --check` pass.

CPU không chạy GPU/model/PA; không dùng CPU record để chứng minh G1/B0.
Sandbox process helper lỗi khởi tạo; lệnh local dùng escalation theo policy,
không đổi cấu hình sandbox hoặc môi trường global.

## Account, budget và nghiên cứu P1

Đã chạy read-only profile/token info với `MODAL_PROFILE=vuonghungnguyen07`;
workspace và user xác minh đúng. Không đổi profile mặc định toàn máy. Evidence
không lưu token ID/secret. Group cloud dùng dependency đã khóa từ uv.lock;
không cài torch/vLLM/CUDA hoặc tải model local.

`configs/modal_dev.yaml` khai báo 30 USD/thí nghiệm; chưa xác minh số dư/usage
billing hiện hành, nên chưa gọi job. Ngân sách cấu hình không là billing cap.

TinyFish search/fetch nguồn chính thức cho model/runtime; một nhánh search
timeout, direct fetch official cards/API/config/tagged docs thành công.
Hai agent research chỉ nhận scope P1, không dữ liệu/gold/credentials, không
cloud job. Kết quả đã được tác giả tổng hợp trong design:

- Qwen3-14B: 14,768,307,200 parameters, revision đầy đủ và 8/8 shard có
  history trước cutoff; Apache-2.0.
- Qwen2.5-Coder-14B-Instruct: 14,770,033,664 parameters, revision đầy đủ và
  6/6 shard có history trước cutoff; Apache-2.0.
- BF16 weights khoảng 27.51 GiB; fit thực tế trong 30 GiB vẫn là giả thuyết.
- Modal RTX-PRO-6000 có sm_120; vLLM0.11.1/torch2.9/cu128/Python3.11 là
  phương án thiết kế, chưa chạy kernel thật. Mọi GPU dependency chỉ cloud.
- Staging CPU online → Volume read-only → GPU offline; 50 câu synthetic,
  hai engine/process mới tuần tự; valid JSON/repeatability/memory đo riêng.

Builder check do agent độc lập thực hiện trên design và source được phép.
Reviewer hỏi mức độc lập hai lượt; đã định nghĩa hai OS subprocess/LLM engine
mới, cùng GPU container, không cache engine dùng chung và phải cleanup trước
lượt sau. Đã làm rõ cutoff theo pinned weights history. Reviewer đọc lại:
"nothing important left". Đây là kiểm tính đủ của thiết kế, không code review
hoặc xác nhận GPU/PA/chi phí thực.

## Handoff

Theo skill brainstorming, cần người dùng duyệt bản thiết kế cụ thể trước
implementation adapter/dependency GPU/job. Đã gửi câu hỏi duyệt; chưa có
phản hồi tại thời điểm ghi báo cáo. Chưa tạo implementation plan như thể đã
được duyệt. Sau duyệt: writing-plans cho đúng design, thực hiện inline theo
lựa chọn người dùng, TDD guard/validator, CPU gate rồi mới preflight/job Modal.

P1 vẫn in_progress; không đổi acceptance, không mở P2 và không có PA/B0 mới.
