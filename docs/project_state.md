# Trạng thái dự án

Cập nhật 01/11/2026, giờ Việt Nam.

**Phase hiện tại:** P00 đã triển khai contract/runner stub/validator và nghiệm thu cấu trúc trên kit thật theo thể lệ. Người dùng xác nhận BTC không có runner/evaluator riêng; không chờ executable BTC. Sẵn sàng P01. Chưa B0.

**Phiên bản chạy ổn định:** package `datamate` 0.1.0, CPython 3.11.18, uv 0.13.6, dependencies trong `uv.lock`. Không chọn model thật.

**Bằng chứng gần nhất:** 34 tests pass + lint/format. P00 kiểm tra 3.000 train + 1.000 public: input refs/schema, submission đầy đủ ID, log/answer khớp; không mở gold. Shell entrypoint pass synthetic. Hash kit nguyên trạng. Kết quả ở `reports/p00_results.md`, `reports/p00_contract_checks.json`; S00 cloud smoke lịch sử ở `reports/s00_setup.md`.

**Config:** `configs/smoke.yaml` cho fixture nhỏ; `configs/modal_dev.yaml` profile/workspace `vuonghungnguyen07`, ngân sách 30 USD/thí nghiệm. Token đã xác thực; không đổi active profile của máy. Source core không phụ thuộc Modal SDK.

**Quyết định còn hiệu lực:** plan v1.3; Docker hoãn toàn bộ tới P13 sau khi pipeline hoàn chỉnh, không chặn S00/P00–P12. Giữ nguyên Dockerfile/.dockerignore nháp. Modal Image vẫn dùng cho cloud. Local chỉ CPU nhẹ/fake; model thật trên Modal; không đọc gold vào inference; chưa upload dữ liệu BTC; không dùng public/private test để training/tuning. Raw giữ nguyên, hash trong `manifests/kit_files.json`.

**Chưa kiểm chứng / việc về sau:** scorer project/matching/PA (P02); GPU/model/offline model (P04); full runtime/budget và Docker (P13); revision kit upstream; quyền upload kit; backup ngoài ổ D. Deadline 16/11/2026 23:59 GMT+7 đã đối chiếu trang chủ BTC ngày 01/11/2026.

**Việc tiếp theo có phạm vi rõ:** P01 inventory metadata/cấu trúc và khóa manifest chia development/calibration/holdout theo business, tránh nghiên cứu sâu câu/nhãn trước khi khóa. P02 sau đó xây scorer từ quy tắc chấm thành văn và diagnostic oracle; chỉ các quy tắc chưa rõ mới mang policy provisional. Không chờ scorer/runner BTC, không làm Docker hoặc chọn model trong P01.

**Cách tiếp tục ở phiên mới:** đọc README → file này → tasks/backlog.json → docs/requirements.md, kiểm tra diff rồi chạy `uv run --locked python scripts/check.py`. Không coi trạng thái kế hoạch ban đầu là bằng chứng công việc đã hoàn thành.
