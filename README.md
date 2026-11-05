# DataMate

Dự án triển khai theo [Timeline DataMate A–G](<Research/Timeline DataMate theo nhóm việc A–G.docx>).
Bản [timeline Markdown đọc trực tiếp trên web](Research/Timeline_DataMate_A-G.md)
có đầy đủ văn bản, bảng và sơ đồ từ DOCX gốc.
Bắt đầu lại theo timeline từ 04/11/2026, kế thừa phần nền đã kiểm thử.
Đã có loader raw CSV/XLSX/SQLite → DuckDB và cache theo business, được kiểm
chứng trên toàn train; có profile raw và schema descriptor phần engineering
A-T2. Chưa có scorer, model thật hoặc PA baseline.

Để đọc/review trên web: bắt đầu từ [timeline Markdown](Research/Timeline_DataMate_A-G.md),
[state hiện tại](docs/project_state.md), [backlog](tasks/backlog.json) và
[contract](docs/requirements.md). Source và fixture synthetic được đồng bộ;
kit BTC, model, credentials và run artifacts giữ local.

## Bắt đầu phiên làm việc

```powershell
$env:PATH = "$PWD\.tools\uv;$env:PATH"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.uv-python"
uv sync --locked
uv run --locked python scripts/harness.py context --task A-T2
uv run --locked python scripts/check.py
```

Đọc [trạng thái](docs/project_state.md), [backlog](tasks/backlog.json), timeline và
[contract](docs/requirements.md) trước khi sửa. Dùng interpreter `.venv/Scripts/python.exe`,
không dùng Python MSYS2 trên PATH. Phiên bản Python được pin ở `.python-version`,
dependency được khóa trong `uv.lock`.
Skill repo `$datamate-increment` dùng cùng tracker; [hướng dẫn harness](docs/harness.md).

## Phần nền giữ lại

| Nhóm timeline | Có thể dùng ngay | Chưa được coi là hoàn thành |
|---|---|---|
| A — Dữ liệu | [Khảo sát sâu train A-T1](docs/research/a_t1_deep_survey.md); [loader/cache DuckDB](docs/ingestion.md); [profile raw/schema descriptor engineering](docs/profiling.md) | A-T2 tự dò encoding/header và kiểm prompt baseline; cleaning production A-T3/T4 |
| E — Đánh giá | Strict output schema, validator input/submission/log | Matching scorer, run_eval, split/access policy, phân tích lỗi và PA |
| G — Hạ tầng | uv/lock, CLI, fake runner, logging/hash, CPU gate/CI, Modal CPU smoke | GPU/model thật, cache/resume production, throughput và Docker offline |
| B/C/D/F | Contract, config và giao diện để phát triển tiếp | Chưa triển khai module nghiệp vụ/ngôn ngữ/agent/huấn luyện |

Nguồn và giới hạn bằng chứng kế thừa: [foundation](docs/foundation.md).
Chỉ bắt đầu task mới trong phạm vi được giao; chưa tạo module rỗng theo tên thư mục timeline.
A-T1 đã hoàn thành. **A-T2** chỉ triển khai phần engineering theo yêu cầu
05/11; research tự dò encoding/header và chiến lược biểu diễn cho LLM được
hoãn. E-T1 và C-T1 vẫn có thể lên kế hoạch theo tracker.

## Công cụ hiện có

```powershell
uv run --locked python scripts/doctor.py
uv run --locked datamate smoke --config configs/smoke.yaml
uv run --locked python scripts/inventory.py --input data/train --output runs/inventory-new
uv run --locked datamate validate-input --input data/train
uv run --locked python scripts/audit_kit.py
uv run --locked datamate ingest --input data/train --cache runs/raw-cache --output runs/ingest-first
uv run --locked python scripts/verify_ingest.py --input data/train --report runs/ingest-first/ingest.json --output runs/ingest-audit
uv run --locked datamate profile --input data/train --ingest-report runs/ingest-first/ingest.json --output runs/profile-first
uv run --locked python scripts/verify_profile.py --input data/train --report runs/profile-first/profile.json --output runs/profile-audit
```

Smoke chỉ chạy hai câu synthetic: tổng bằng `12.35` và mã `0012`. SQL fixture tin cậy,
không phải worker an toàn cho SQL do model sinh. Local được giới hạn ở 2 threads,
DuckDB 256 MiB, fixture tối đa 1 MiB. Inventory chỉ kiểm tra cơ học; chưa đọc header/sheet/catalog.
Output inventory phải mới và ở ngoài input, kể cả alias/junction.

Loader giữ cả header/lời dẫn/tổng/dòng trùng và hàng trống vật lý; không tự
parse tiền/ngày, chọn header, fill nhóm hoặc dedup. Mỗi business có một DB,
mỗi CSV/sheet/bảng có một view với cột positional và metadata nguồn. Chạy lại
với cùng cache và output report mới để dùng cache hit. Cách truy vấn, giới hạn
và xử lý lỗi: [hướng dẫn ingestion](docs/ingestion.md). Bằng chứng nghiệm thu:
[kết quả A-T1](reports/a_t1_loader_results.md).

Profiler thống kê đầy đủ raw, phân biệt missing/NULL/rỗng, giữ kiểu vật lý,
mẫu có tọa độ và min–max có định nghĩa rõ. CSV/XLSX header mặc định unresolved;
chỉ nhận annotation tường minh gắn fingerprint. Encoding là cấu hình loader,
không được gọi là detection. JSON schema dùng tên view/cột raw thật; đã kiểm
consumer synthetic, chưa có prompt/model baseline. Profile có mẫu BTC phải
giữ trong `runs/`. Xem [hướng dẫn profile](docs/profiling.md) và
[phạm vi engineering A-T2](docs/research/a_t2_engineering.md).
Bằng chứng full train, determinism và kiểm chứng SQL riêng:
[nghiệm thu engineering A-T2](reports/a_t2_engineering_results.md).

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
Chưa build/test Docker. [CPU gate trên GitHub Actions](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/actions/runs/41872674037)
đã pass cho source commit `c69d4da`; bằng chứng local và CI được ghi riêng trong
[báo cáo publish](reports/github_publish.md).

Chi tiết giữ/xóa và backup: [báo cáo reset](reports/timeline_reset_results.md).
Repo: https://github.com/vuongnguyen16/ZaloAI2026_Datamate.
