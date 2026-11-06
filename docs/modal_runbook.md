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
Người dùng cho phép tối đa 30 USD/thí nghiệm; đây không phải giới hạn chi tiêu cứng do SDK áp đặt.
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

Nếu build/run lỗi: đọc log tại URL do CLI trả về, sửa nguyên nhân trước khi retry. Terminal
mất kết nối thì kiểm tra app trước khi nộp lại để tránh job trùng. Tìm app bằng
`modal app list`; dừng đúng app bằng `modal app stop APP_ID` khi cần.
Kiểm tra app và chi phí ở dashboard workspace. Chưa có bill thì ghi chưa có,
không ghi 0 USD. Timeout một function không giới hạn chi phí nhiều lần build/run.

Model integration thuộc D/G: eligibility ≤15B gồm auxiliary/MoE, full revision,
license/cutoff, tokenizer/template, cloud runtime, output thật và budget phải có
trước khi khẳng định model adapter hoạt động. Không tạo Volume/tải weights như side effect cleanup.
Docker offline/full run ở P3 thuộc G, sau lát cắt P2/G2; không chờ tối ưu P4–P8.

## P1 model probe

Thiết kế đã duyệt ở `docs/research/p1_modal_design.md`; plan thực hiện ở
`docs/research/p1_modal_plan.md`. `scripts/p1_probe.py check` chỉ đọc account,
app và kiểm billing. `run` mới build Image/Volume và gọi staging/GPU.
Không gọi trực tiếp infra để bỏ qua preflight.

```powershell
$env:MODAL_PROFILE = 'vuonghungnguyen07'
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.uv-python"
uv run --locked --group cloud python scripts/p1_probe.py check --model Qwen/Qwen3-14B --billing-json .tmp/p1-billing.json
uv run --locked --group cloud python scripts/p1_probe.py run --model Qwen/Qwen3-14B --billing-json .tmp/p1-billing.json
```

Billing JSON giữ local, gồm `available_usd`, `checked_at` ISO có timezone và
`source` (`user-confirmed` hoặc `dashboard`); bằng chứng phải trong24h, không
ở tương lai và đủ dự toán. Không đưa token/credential vào file này. Ceiling
30USD vẫn không phải hard cap. Không tự retry khi mất kết nối; đọc events/app
trước. CLI chặn app P1 đang hoạt động để tránh submit trùng.

Các candidate được ghim trong `manifests/models.json`; `inference_models`
giữ rỗng cho tới khi chọn model từ evidence thật. CUDA OCI digest ở
`configs/p1_runtime.json`; dependency/uv.lock riêng trong `infra/p1_runtime/`.
**Không sync project GPU đó local.** Chỉ resolve lock local; cloud mới install.
CPU CI không import torch/vLLM/Modal khi collection.

Chỉ allowlist code, lock, model metadata và fixture synthetic được gửi cloud.
50 câu phủ9type, hai engine subprocess mới trong cùng GPU container, serial,
không tái dùng engine/prefix cache. Weights stage online trên CPU rồi hash;
GPU chỉ đọc Volume, block_network và local-files-only. Volume giữ weights cho
P2 và tiếp tục có chi phí storage; không tự xóa như cleanup.

Sau review, thêm Volume evidence synthetic riêng với UUID được ghi trong
events local. Weights vẫn read-only; checkpoint round được commit trước khi
chạy round kế tiếp. Khi mất kết nối, kiểm app và evidence UUID trước khi tính
chạy lại. SDK chọn Python series3.11, cloud uv cài worker interpreter3.11.18;
không cài interpreter/GPU dependency khác vào môi trường local.

Mỗi run tạo `runs/p1-probe-.../`: preflight/config/model/source hash,
synthetic fixture local, events/app ID, raw_result và acceptance. Expected của
fixture không vào inference payload. Timeout/failure được ghi, không repair
JSON hoặc biến fake thành G1. Bộ nhớ là target vLLM30GiB và peak đo, không
phải physical GPU partition. Bằng chứng synthetic này không phải PA/B0.

Phạm vi P2 đã được chủ project xác nhận: dev/input/câu hỏi và artifact tối
thiểu của dev trên Modal, không gold inference/calibration/holdout. Xem
`docs/research/p2_g2_g5_decisions.md`; account/budget/data manifest vẫn kiểm
trước job. P1 CLI ở trên vẫn chỉ50fixture synthetic; probe P2 là integration
riêng, không thay fixture/expected P1 bằng câu BTC hoặc claim G1 cho workload mới.
