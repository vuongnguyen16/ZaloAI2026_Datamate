# Vận hành Modal cho DataMate

Profile và workspace của dự án là `vuonghungnguyen07`. Không đổi active profile của toàn máy; đặt biến cho terminal đang dùng. SDK nằm trong group `cloud`, không phải dependency của core.

```powershell
$env:PATH = "$PWD\.tools\uv;$env:PATH"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.uv-python"
$env:MODAL_PROFILE = "vuonghungnguyen07"
uv sync --locked --group cloud
uv run --locked --group cloud modal profile list --json
uv run --locked --group cloud modal token info
```

Hai lệnh cuối chỉ kiểm tra tài khoản, không khởi tạo GPU/job. Không gửi nội dung token vào repo/chat/log. Nếu credential hết hạn, người dùng chạy `uv run --locked --group cloud modal setup` và đăng nhập đúng workspace; không cần làm lại khi token còn hiệu lực.

## Smoke CPU synthetic

Trước mỗi thí nghiệm, kiểm tra `configs/modal_dev.yaml`: đúng profile/workspace và `budget_usd_per_experiment` dương, không vượt ngân sách được giao. Người dùng cho phép tối đa **30 USD/thí nghiệm**. Đó là ngân sách, không phải hard spending limit của SDK; dashboard workspace cần được kiểm tra riêng.

```powershell
uv run --locked --group cloud modal run infra/modal_app.py
```

Chỉ dùng entrypoint `main` này; nó kiểm tra profile và ngân sách trước `.remote()`. File app có allowlist source/config/lock/synthetic rõ ràng, không mount data/, answers, credentials, runs hay toàn bộ repo. Image cài core từ `uv.lock`; ép index PyPI khớp lock để tránh mirror Modal làm lock bị coi là thay đổi. Linux venv được build trong image.

Function dùng 1 CPU, 512 MiB, tối đa 1 container, không min/buffer container, scaledown 2s, timeout 120s, startup 300s, retries=0. Không dùng GPU hoặc model. Image build có thể dùng mạng ở setup; function chạy với `block_network=True`, probe request ngoài phải thất bại rồi smoke chạy bằng file có sẵn.

Kết quả trả về `runs/modal-cpu-.../`, gồm artifact gốc và `remote_summary.json` với image ID, hash infra/artifact, profile, thời gian và network probe. Dữ liệu synthetic có đáp án tự tính `12.35` và `0012`. Đây là smoke hệ thống, không phải đánh giá model hoặc PA.

Nếu lỗi build: đọc log image/app từ URL CLI trả về, sửa nguyên nhân rồi mới chạy lại. Khi terminal mất kết nối, kiểm tra app trên dashboard trước khi nộp lại để tránh hai job trùng. Không tự tăng retries/concurrency hoặc fallback model local.

## Dừng và kiểm tra chi phí

CLI in URL run dưới workspace này. Kiểm tra app và usage/billing trên [Modal dashboard](https://modal.com/apps/vuonghungnguyen07/main). Function/job không phải service GPU thường trực. Dùng `modal app list` tìm đúng app ID; `modal app stop APP_ID` dừng app nếu còn chạy. Không suy ra job đã dừng chỉ vì terminal đóng.

Chi phí thực tế phải lấy từ usage/billing sau khi cập nhật; `remote_summary.json` để `billing_usd=not_yet_available` nếu chưa có dữ liệu. Không ghi 0 USD chỉ vì chưa thấy bill. Timeout một function không giới hạn tổng chi phí của nhiều lần build/run.

## Nghiệm thu Docker trên cloud phù hợp

**Hoãn tới P13 sau khi pipeline hoàn chỉnh, theo quyết định chủ dự án ngày 01/11/2026.** Các lệnh trong mục này chỉ là tham chiếu cho lúc đó; không thực hiện hoặc xem là blocker hiện tại. Modal Image cho các phép thử cloud không bị hoãn.

`Dockerfile` hiện là ứng viên CPU, chưa được nghiệm thu trên host Docker. Nó không chứa model và chưa phải artifact nộp. Build và thử trên host cloud hỗ trợ Docker, không giả định Docker daemon có trong Modal Function. Ví dụ Bash:

```bash
docker build -t datamate:cpu .
mkdir -p runs/docker-stub
# Cấp quyền output phù hợp UID 10001 của image trước khi bind mount.
docker run --rm --network none \
  --mount type=bind,src="$PWD/tests/fixtures/synthetic",dst=/data,readonly \
  --mount type=bind,src="$PWD/runs/docker-stub",dst=/result \
  datamate:cpu
```

Ghi image digest và kiểm tra /data read-only, output/log/quyền user, cache mới và cold start khi chạy thật. Base tag đã pin version nhưng digest OCI còn chờ build/inspection. CPU smoke Modal chặn egress chưa chứng minh đầy đủ hợp đồng Docker BTC.

P04 sẽ thêm model eligibility/full revision/Volume/engine/GPU probe. Không tạo Volume hoặc tải weights trước khi đến quyết định đó. Inference cuối dùng EngineAdapter trong cùng môi trường BTC, không phụ thuộc RPC Modal.
