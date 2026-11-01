# Môi trường DataMate

Kiểm kê ngày 01/11/2026, giờ Việt Nam, từ máy thật. Đây là trạng thái phát triển, không phải máy BTC.

| Mục | Quan sát / quyết định |
|---|---|
| Workspace | `D:\ZaloAI_2026` |
| OS | Windows build `10.0.26200`, x86-64; API Python/.NET có thể ghi nhãn Windows 10/11 khác nhau |
| CPU | Intel64 Family 6 Model 151 Stepping 2; 12 logical CPUs. Chưa xác minh tên thương mại/số lõi vật lý vì WMI/CIM bị từ chối |
| RAM vật lý | 16,890,322,944 bytes, khoảng 15.73 GiB |
| RAM khả dụng lúc đo | Khoảng 1.8–2.0 GiB; giá trị tức thời, không dành toàn bộ cho project |
| Ổ D | NTFS, 262,142,947,328 bytes; khoảng 122.8 GiB trống sau setup. Chưa xác minh loại SSD/HDD |
| Git | `2.51.0.windows.2` |
| uv | `0.13.6`, cài riêng ở `.tools/uv/`; không sửa PATH hệ thống |
| Python project | CPython `3.11.18` managed trong `.uv-python/`, `.venv/Scripts/python.exe` |
| Python trên PATH ban đầu | MSYS2 Python `3.12.11`; không dùng cho project |
| CPU dependencies đã chạy | DuckDB 2.0.0, Pydantic 2.14.2, PyYAML 6.0.3; pytest 9.2.0, Ruff 0.17.3; resolution chi tiết trong `uv.lock` |
| Modal SDK | `1.6.3`, group `cloud`, core không import SDK |
| Git remote | `https://github.com/vuongnguyen16/ZaloAI2026_Datamate.git`; đã gắn `origin`, chưa push |
| Docker local | Đường dẫn khả dụng khác nhau giữa execution context; chưa xác minh daemon và không chạy Docker local trong phiên này |

WMI/CIM trả `Access denied`; RAM được đo lại bằng Windows `GlobalMemoryStatusEx`, CPU logical bằng Python/.NET, disk bằng DriveInfo/shutil. Không suy đoán tên CPU hoặc loại ổ từ model máy. `scripts/doctor.py` tái kiểm kê, không đọc token và không gọi cloud.

## Phân công tài nguyên

Local dùng viết code/Git/lint/test và fixture synthetic nhỏ. Config khởi đầu giới hạn 2 threads, DuckDB memory 256 MiB, fixture tổng tối đa 1 MiB và 100 câu. Memory limit này chỉ áp dụng DuckDB, không phải giới hạn RAM cứng của cả process. Inventory nặng/ingestion thật chuyển Modal CPU khi cần.

Mọi model thật, kể cả embedding/reranker nhỏ, chạy Modal. Không tải weights/cài CUDA, PyTorch hoặc vLLM local. Unit test dùng fake adapter.

Profile và workspace được người dùng sửa tên và xác nhận: **`vuonghungnguyen07`**. SDK đã tìm thấy profile; `MODAL_PROFILE=vuonghungnguyen07 modal token info` đã xác thực thành công. Không đổi profile mặc định toàn máy, không ghi token vào repo/log.

Người dùng cho phép **tối đa 30 USD/thí nghiệm**. Trần này được lưu trong `configs/modal_dev.yaml`; đó là ngân sách cho phép, không phải chức năng hard cap tiền của SDK. Mỗi job vẫn cần timeout/concurrency/retry và kiểm tra usage của workspace. Chưa xác minh spending limit/credits/quota GPU trên dashboard.

Smoke CPU Modal được chuẩn bị với 1 CPU, 512 MiB, tối đa 1 container, không giữ container chờ, timeout function 120s, startup 300s, không retry. Xem kết quả thực ở `reports/s00_setup.md`. Không cấp GPU ở S00. Lịch GPU smoke: P04, sau khi kiểm tra model eligibility và engine/GPU khả dụng; thực hiện trước B0.

## Nơi lưu và khôi phục

- Kit nguyên trạng: `data/train/`, `data/public_test/`; hash trong `manifests/kit_files.json`.
- Fixture được commit: `tests/fixtures/synthetic/`.
- Run/log local và artifact tải từ cloud: `runs/`, bị Git ignore.
- Model thật: dự kiến Modal Volume theo full revision, thiết lập ở P04; chưa tạo Volume hoặc tải model.
- Source/config/docs: Git local và remote do người dùng chỉ định. Chưa upload dữ liệu BTC.
- Kit và artifact lớn chưa có backup ngoài ổ D được xác minh; Git ignore không phải backup hoặc cơ chế bảo mật.
