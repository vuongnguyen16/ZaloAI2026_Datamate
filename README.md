# DataMate

Khởi tạo dự án theo `Research/DataMate_Research_Build_Plan.md` v1.2.
Hiện tại có CPU smoke bằng fake adapter và stub kiểm tra format; chưa có model thật hoặc B0.

## Chạy trên Windows PowerShell

Python được pin ở `.python-version`; dependency được khóa bằng `uv.lock`.
Nếu `uv` chưa có trên PATH, dùng bản workspace:

```powershell
$env:PATH = "$PWD\.tools\uv;$env:PATH"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.uv-python"
uv sync --locked
uv run --locked python scripts/doctor.py
uv run --locked python scripts/check.py
uv run --locked datamate smoke --config configs/smoke.yaml
```

Editor chọn interpreter `.venv/Scripts/python.exe`. Không dùng Python MSYS2 trên PATH để chạy project.
Máy khác cài [uv chính thức](https://docs.astral.sh/uv/getting-started/installation/), rồi chạy cùng lệnh `uv sync --locked`.
Không cần activate venv khi dùng `uv run`. Core không cài engine GPU.

Smoke dùng hai câu synthetic: tổng `12.34 + 0.01 = 12.35` và mã `0012` giữ số 0 đầu.
Kết quả trong thư mục mới `runs/smoke-.../`: submission, predictions, log từng câu, manifest hash, config và summary.
Đường dẫn trong YAML tính từ thư mục chứa YAML. SQL trong smoke là fixture tin cậy; worker SQL cho model chưa triển khai.

## Stub theo format thể lệ được cung cấp

```powershell
uv run --locked datamate stub --input data/train --output runs/train-format-stub
```

Stub chỉ đọc `questions.jsonl`, xuất mỗi ID một `abstain`; không đọc gold hoặc dữ liệu doanh nghiệp.
Thư mục output phải mới/trống để tránh trộn run. `predict.sh` gọi stub với `/data` và `/result` theo thể lệ.
Chưa có evaluator/runner/Docker guide chính thức trong workspace để xác nhận tương thích đầy đủ.
`predict` thật ở P05 và `evaluate` ở P02 chưa có; không dùng stub để báo chất lượng model.

## Local và Modal

Local chỉ viết code, lint/test, fixture nhỏ: 2 threads, DuckDB 256 MiB, fixture tối đa 1 MiB.
Mọi model thật chạy Modal, kể cả embedding/reranker hoặc model CPU nhỏ. Không tải weights về laptop.
Profile và workspace người dùng cung cấp: `vuonghungnguyen07`; xem `configs/modal_dev.yaml` và `docs/modal_runbook.md`.
Đã xác thực profile và chạy thành công smoke CPU Modal có chặn egress. Ngân sách người dùng: tối đa 30 USD/thí nghiệm.
GPU/quota/billing thực tế chưa đo; xem `reports/s00_setup.md`.

## Trạng thái và dữ liệu

Đọc `docs/project_state.md`, `docs/environment.md`, `docs/requirements.md` và `tasks/backlog.json`.
`data/`, model, runs, credentials và thể lệ gốc được giữ local qua `.gitignore`.
Chưa upload dữ liệu BTC hoặc push lên GitHub. Chỉ fixture synthetic được quản lý trong source.
Repo dự án: https://github.com/vuongnguyen16/ZaloAI2026_Datamate.
