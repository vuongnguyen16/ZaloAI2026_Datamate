# DataMate

Lộ trình hiện hành: [Timeline một người theo giai đoạn](Research/Timeline_DataMate_A-G.md),
nguồn [DOCX](<Research/Timeline DataMate theo nhóm việc A–G.docx>) cập nhật 05/11/2026.
Triển khai tuần tự P0–P9, mỗi pha có cổng kiểm chứng. A–G là nhóm chuyên môn,
không còn là bảy luồng song song theo tuần. Ước lượng trong DOCX là ngày công.

**P0/G0 đã hoàn tất:** split/access khóa, scorer 9 type,
run_eval/bootstrap và taxonomy dev đã có. [Kết quả](reports/p0_results.md),
[cách đánh giá](docs/evaluation.md). Calibration/holdout gold giữ kín;
**P1/G1 đã hoàn tất:** hai model thật trên Modal sm_120, JSON50/50 mỗi lượt,
hai lượt trùng; peak<30GiB, weights read-only và inference offline.
[Kết quả P1](reports/p1_results.md). Chưa có B0/PA dữ liệu BTC;
bước tiếp theo là P2 hybrid pipeline.
Tracker duy nhất là [backlog](tasks/backlog.json) và [state](docs/project_state.md).

## Bắt đầu phiên

```powershell
$env:PATH = "$PWD\.tools\uv;$env:PATH"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.uv-python"
uv sync --locked
uv run --locked python scripts/timeline.py check
uv run --locked python scripts/harness.py context --task P2
uv run --locked python scripts/check.py
```

Chưa có uv PATH thì gọi `.tools/uv/uv.exe`. Dùng Python `.venv/Scripts/python.exe`,
không dùng MSYS2 Python. Dependency chỉ qua pyproject.toml + uv.lock.
Đọc AGENTS, state, backlog, DOCX và [contract](docs/requirements.md) trước sửa;
dùng skill `$datamate-increment` và [harness](docs/harness.md).

Tra cứu quan hệ code bằng [Graphify local](docs/graphify.md), skill `$graphify`:
`python scripts/graphify_local.py query "run_eval read_scoped"`.
Graph chỉ gồm code, không có dữ liệu BTC/gold; dependency tool khóa riêng.

[Archify](docs/archify.md), skill `$archify`, đã cài theo workspace để tạo sơ đồ
và trang onboarding HTML local có source evidence cho đồng nghiệp mới.

[Superpowers](docs/superpowers.md) đã tích hợp theo dự án: 15 skill gốc cho
thiết kế, plan, TDD, debug và review; bootstrap qua AGENTS.md. Dùng chung với
`$datamate-increment` và `$graphify`, theo các ràng buộc dữ liệu/gate của repo.

## Phần đã có

| Thành phần | Bằng chứng và giới hạn |
|---|---|
| A-T1 loader CSV/XLSX/SQLite → DuckDB, cache raw | [Hướng dẫn](docs/ingestion.md), [nghiệm thu](reports/a_t1_loader_results.md); 30 business/339 unit, bảo toàn raw |
| A-T2 format/profile/header/data_start/descriptor | [Profile](docs/profiling.md), [format](docs/runtime_format.md), [nghiệm thu](reports/a_t2_completion_results.md); 311 auto/11 unresolved/17 schema; actual prompt/PA còn ở P2 |
| P0 đánh giá | [Scorer/scoped reader/bootstrap/taxonomy](docs/evaluation.md); [split khóa](docs/split_policy.md); chưa B0/PA BTC |
| P1 model/runtime | [Qwen3-14B và Coder-14B trên Modal](reports/p1_results.md); structured JSON, hai process mới, sm_120 và offline pass; chưa B0/PA |
| Nền G/E | [Foundation](docs/foundation.md): uv/CLI/validator/fake/log/hash/CPU CI; Modal CPU synthetic lịch sử; GPU/model xem P1 |

Kiến trúc mục tiêu: domain_lib dựng từ dev, model nhỏ chọn/gọi hàm,
SQL/Python dự phòng và abstain/verifier/formatter từ P2. single_sql là đối chứng.
Không tạo module rỗng hoặc coi kế hoạch là code đã chạy.

## Công cụ hiện có

```powershell
uv run --locked python scripts/doctor.py
uv run --locked datamate smoke --config configs/smoke.yaml
uv run --locked datamate validate-input --input data/train
uv run --locked python scripts/audit_kit.py
uv run --locked datamate ingest --input data/train --cache runs/raw-cache --output runs/ingest-first
uv run --locked python scripts/verify_ingest.py --input data/train --report runs/ingest-first/ingest.json --output runs/ingest-audit
uv run --locked datamate profile --input data/train --ingest-report runs/ingest-first/ingest.json --output runs/profile-first
uv run --locked python scripts/verify_profile.py --input data/train --report runs/profile-first/profile.json --output runs/profile-audit
uv run --locked datamate split-check --split runs/p0-split-20261105/frozen --manifest-sha256 b28dd4fa7fb34b7a0ed356c7ec11f32f84911bcdf71fcd128c2c5082b208fa18
```

Dùng output mới; không ghi đè input/cache cũ. Loader giữ header/tổng/trùng/trống,
không semantic cleaning. Profile có unresolved fallback; data_start chỉ cận dưới.
Smoke chỉ hai câu synthetic (`12.35`, `0012`), SQL fixture tin cậy, chưa sandbox
SQL do model sinh. Local 2 threads/DuckDB 256 MiB/fixture ≤1 MiB.
`predict.sh` gọi stub `/data` → `/result`, chưa inference thật; validator chỉ
kiểm cấu trúc, không chấm PA. Bằng chứng CPU hiện hành nằm ở state/context.

## Modal, dữ liệu và đóng gói

Mọi model thật/embedding/reranker/huấn luyện chỉ Modal, không tải weights hoặc
cài CUDA/PyTorch/vLLM local. Profile/workspace `vuonghungnguyen07`, tối đa
30 USD/thí nghiệm; xác minh account/budget/phạm vi dữ liệu trước job theo
[runbook](docs/modal_runbook.md). Budget khai báo không phải hard billing cap.

Docker thuộc G tại **P3 sau G2/P2**; draft giữ nguyên tới đó. Không đợi tối ưu
P4–P8 mới đóng gói. Modal Image dùng cho P1. Kit BTC, gold, profile, labels,
runs, model và credentials tiếp tục giữ local/ignored; không publish lên repo.

Kế hoạch tuần và tài liệu đã hết hiệu lực được lưu tại
[archive/timeline-20261103](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/tree/archive/timeline-20261103).
Chỉ tra lịch sử; không phục hồi làm kế hoạch. [Báo cáo đồng bộ](reports/timeline_sync_results.md).
Repo: https://github.com/vuongnguyen16/ZaloAI2026_Datamate.
