# Modal cho nhóm D/G/F

Tất cả model thật và huấn luyện chạy trên Modal. Profile/workspace
`vuonghungnguyen07`; không đổi active profile toàn máy. Core không import SDK.

## Xác minh trước job

```powershell
$env:PATH = "$PWD\.tools\uv;$env:PATH"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.uv-python"
$env:MODAL_PROFILE = "vuonghungnguyen07"
uv sync --locked --group cloud
uv run --locked --group cloud modal profile list --json
uv run --locked --group cloud modal token info
```

Hai lệnh cuối chỉ kiểm tra account; không ghi token vào repo/log. Nếu credential
hết hạn, dùng `modal setup` và đăng nhập đúng workspace. Không gọi job trước khi
xác minh lại profile và budget trong `configs/modal_dev.yaml`.
Người dùng cho tối đa 30 USD/thí nghiệm; đây không là hard spending limit SDK.
Kiểm tra usage/billing và giới hạn job/retry/concurrency; chưa đo quota GPU.

## CPU smoke synthetic có sẵn

```powershell
uv run --locked --group cloud modal run infra/modal_app.py
```

Lệnh này tạo job cloud, chỉ chạy khi task đã yêu cầu kiểm chứng remote. Dùng
local entrypoint để chặn profile/budget sai trước `.remote()`. App chỉ copy
allowlist source/config/lock/synthetic; không mount data/gold/credentials/runs
hoặc toàn repo. Image dùng uv.lock, index PyPI khớp lock; không copy venv Windows.

1 CPU/512 MiB, tối đa 1 container, min/buffer=0, scaledown 2s, function timeout
120s/startup 300s/retries 0; không GPU/model. Function block_network và probe
outbound phải thất bại. Kết quả `runs/modal-cpu-.../` chứa remote summary/hash.
Kết quả lịch sử ngày 01/11 ở `docs/foundation.md`; không suy ra model/PA pass.
Tên app lịch sử được giữ để còn đối chiếu run cũ.

## Dừng và chẩn đoán

Nếu build/run lỗi: đọc log URL CLI trả, sửa nguyên nhân trước retry. Terminal
mất kết nối thì kiểm tra app trước nộp lại để tránh job trùng. Tìm app bằng
`modal app list`; dừng đúng app bằng `modal app stop APP_ID` khi cần.
Kiểm tra app và chi phí ở dashboard workspace. Chưa có bill thì ghi chưa có,
không ghi 0 USD. Timeout một function không giới hạn chi phí nhiều lần build/run.

Model integration thuộc D/G: eligibility ≤15B gồm auxiliary/MoE, full revision,
license/cutoff, tokenizer/template, cloud runtime, output thật và budget phải có
trước claim model adapter. Không tạo Volume/tải weights như side effect cleanup.
Docker offline/full run giữ tới bước đóng gói nhóm G sau pipeline hoàn chỉnh.
