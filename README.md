# DataMate

Dự án triển khai theo [Timeline DataMate A–G](<Research/Timeline DataMate theo nhóm việc A–G.docx>).
Bản [timeline Markdown đọc trực tiếp trên web](Research/Timeline_DataMate_A-G.md)
có đầy đủ văn bản, bảng và sơ đồ từ DOCX gốc.
Bắt đầu lại theo timeline từ 04/11/2026, kế thừa phần nền đã kiểm thử.
Chưa có loader đa định dạng, scorer, model thật hoặc PA baseline.

## Bắt đầu phiên làm việc

```powershell
$env:PATH = "$PWD\.tools\uv;$env:PATH"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.uv-python"
uv sync --locked
uv run --locked python scripts/harness.py context --task A-T1
uv run --locked python scripts/check.py
```

Đọc [trạng thái](docs/project_state.md), [backlog](tasks/backlog.json), timeline và
[contract](docs/requirements.md) trước sửa. Dùng interpreter `.venv/Scripts/python.exe`,
không dùng Python MSYS2 trên PATH. Python pin ở `.python-version`, dependency ở `uv.lock`.
Skill repo `$datamate-increment` dùng cùng tracker; [hướng dẫn harness](docs/harness.md).

## Phần nền giữ lại

| Nhóm timeline | Có thể dùng ngay | Chưa được coi là hoàn thành |
|---|---|---|
| A — Dữ liệu | Inventory file/hash/câu theo business; bảo vệ raw | Khảo sát dòng/cột/README, CSV/XLSX/SQLite loader, profile/cleaning |
| E — Đánh giá | Strict output schema, validator input/submission/log | Matching scorer, run_eval, split/access policy, phân tích lỗi và PA |
| G — Hạ tầng | uv/lock, CLI, fake runner, logging/hash, CPU gate/CI, Modal CPU smoke | GPU/model thật, cache/resume production, throughput và Docker offline |
| B/C/D/F | Contract, config và giao diện để phát triển tiếp | Chưa triển khai module nghiệp vụ/ngôn ngữ/agent/huấn luyện |

Nguồn và giới hạn bằng chứng kế thừa: [foundation](docs/foundation.md).
Chỉ bắt đầu task mới trong phạm vi được giao; chưa tạo module rỗng theo tên thư mục timeline.
Task đầu tiên sẵn sàng là **A-T1**, cùng các việc E-T1 và C-T1 có thể lên kế hoạch tiếp.

## Công cụ hiện có

```powershell
uv run --locked python scripts/doctor.py
uv run --locked datamate smoke --config configs/smoke.yaml
uv run --locked python scripts/inventory.py --input data/train --output runs/inventory-new
uv run --locked datamate validate-input --input data/train
uv run --locked python scripts/audit_kit.py
```

Smoke chỉ chạy hai câu synthetic: tổng `12.35` và mã `0012`. SQL fixture tin cậy,
không phải worker an toàn cho SQL do model sinh. Local giới hạn 2 threads,
DuckDB 256 MiB, fixture tối đa 1 MiB. Inventory chỉ cơ học; chưa đọc header/sheet/catalog.
Output inventory phải mới và ở ngoài input, kể cả alias/junction.

`datamate stub --input INPUT --output OUTPUT` chỉ xuất abstain/log theo format.
`predict.sh` hiện gọi stub tại `/data` → `/result`; chưa phải inference thật.
`validate-submission` và `validate-logs` kiểm tra cấu trúc, không chấm PA.
`scripts/verify_contract.py` kiểm tra input/stub/submission/log cả train và public
theo contract, không parse gold; ghi report vào `reports/contract_checks.json`.

## Modal, dữ liệu và đóng gói

Mọi model thật chạy Modal; local không tải weights hoặc cài CUDA/PyTorch/vLLM.
Profile/workspace `vuonghungnguyen07`, tối đa 30 USD/thí nghiệm; xác minh lại trước
job theo [runbook](docs/modal_runbook.md). Trong phiên reset không chạy cloud.

`data/`, models, runs, credentials và thể lệ gốc được giữ local qua `.gitignore`.
Không upload kit khi chưa xác minh quyền; source chỉ dùng fixture synthetic.
Dockerfile/.dockerignore là bản nháp giữ cho nhóm G sau khi pipeline hoàn chỉnh.
Chưa build/test Docker. Workflow CPU sẽ chạy khi push lên GitHub;
kết quả CI cần được kiểm tra riêng với bằng chứng CPU local.

Chi tiết giữ/xóa và backup: [báo cáo reset](reports/timeline_reset_results.md).
Repo: https://github.com/vuongnguyen16/ZaloAI2026_Datamate.
