# Môi trường phát triển

Dữ liệu kiểm kê lịch sử ngày 01/11/2026; không phải máy BTC hoặc số đo mới.

| Mục | Giá trị |
|---|---|
| Workspace/OS | D:\ZaloAI_2026; Windows build 10.0.26200 x86-64 |
| CPU/RAM | 12 logical CPUs; 16,890,322,944 bytes RAM, khoảng 15.73 GiB |
| Python/uv/Git | CPython 3.11.18 managed; uv 0.13.6 workspace; Git 2.51.0.windows.2 |
| Project env | .venv/Scripts/python.exe; không dùng MSYS2 Python trên PATH |
| Dependency | pyproject.toml + uv.lock; core DuckDB/Pydantic/PyYAML, dev pytest/Ruff |
| Modal SDK | Group cloud; không import từ core |

RAM khả dụng lúc kiểm kê khoảng 1.8–2.0 GiB; tên CPU thương mại/SSD chưa xác
minh do WMI/CIM bị từ chối. `scripts/doctor.py` đọc lại thông tin không cần cloud.
Local chỉ CPU nhẹ/fake: 2 threads, DuckDB 256 MiB, fixture ≤1 MiB/100 câu.
Memory limit DuckDB không là hard RAM cap toàn process.

Mọi model thật, embedding/reranker/huấn luyện ở Modal. Profile/workspace
`vuonghungnguyen07`, tối đa 30 USD/thí nghiệm, cần xác minh lại trước job mới.
Cloud CPU smoke lịch sử xem `docs/foundation.md`; GPU/quota/billing chưa đo.

Raw `data/train/`, `data/public_test/`; hash ở `manifests/kit_files.json`.
Fixture source chỉ synthetic. Run/model/credentials không track; chưa upload kit.
Backup kit ngoài ổ D chưa được xác minh; Git ignore không là backup/bảo mật.
