# S00 — Kết quả thiết lập

Ngày 01/11/2026, giờ Việt Nam. CPU harness đã chạy; GPU chưa thử, PA chưa đánh giá. Đây chưa phải B0.

| Cổng | Kết quả | Bằng chứng |
|---|---|---|
| S00-A | Qua, unknown ghi rõ | `docs/environment.md`; inventory máy thật, profile/workspace và ngân sách |
| S00-B/C | Qua | CPython 3.11.18, uv 0.13.6, lock và package src-layout; origin đúng repo; raw/secret/run ignored |
| S00-D/E/F | Qua | README/AGENTS/state/backlog; config/schema/CLI; 20 tests pass và lint/format |
| Cổng cố ý fail | Qua | Thêm tạm assertion sai → check exit 1, 1 failed/19 passed; bỏ probe → pass. Không đổi expected để giấu lỗi |
| S00-H | CPU qua | Token info xác thực profile `vuonghungnguyen07`; người dùng cho ngân sách 30 USD/thí nghiệm; CPU cloud thành công |
| S00-G CPU cloud | Qua trong phạm vi Modal | `block_network=True`, request outbound thất bại; hai output đúng; artifact tải về |
| Docker candidate / máy tương đương BTC | Chưa kiểm chứng | Có Dockerfile/.dockerignore; chưa chạy Docker host và read-only mount contract |
| GPU / model / PA / full offline | Chưa làm | P04/P02/P05/P13, không suy ra từ fake smoke |

## Lệnh và kết quả

`uv` dưới đây là `.tools/uv/uv.exe` khi chưa đưa vào PATH; cache/Python managed nằm trong workspace theo README.

- `uv sync`: exit 0, tạo `.venv` và lock; core import thành công.
- `uv sync --locked`: xác minh lock khớp; môi trường sạch core được kiểm tra riêng, xem phần tái tạo.
- `uv run --locked python scripts/doctor.py`: exit 0; máy x86-64, 12 logical CPUs, RAM khoảng 15.73 GiB, interpreter project 3.11.18.
- `uv run --locked python scripts/check.py`: exit 0; Ruff lint/format và **20 tests passed**. Bộ test gồm tiền/mã, lỗi model giả/SQL, duplicate/missing ID, config/budget, output types và runtime không có Git.
- `uv run --locked datamate smoke --config configs/smoke.yaml`: exit 0; artifact ví dụ `runs/smoke-20261101T061548Z-76f8f6a9/`; tổng 12.35, mã 0012.
- `uv run --locked datamate stub --input data/train --output runs/train-format-stub`: exit 0; 3.000 câu → 3.000 unique output IDs khớp input, toàn bộ abstain, 3.000 log. Không đọc `answers.jsonl`.
- `uv run --locked python scripts/audit_kit.py`: hash 259 data files và thể lệ; train 30/public 14 business directories. Chạy lại phát hiện thay đổi thay vì ghi đè manifest.

## Modal CPU offline smoke

Run thành công: [Modal app ap-V5mZIojkntGhLow7r8ahUW](https://modal.com/apps/vuonghungnguyen07/main/ap-V5mZIojkntGhLow7r8ahUW).
Image ID `im-aw8AXx4XzPdherlbygTxUN`. Artifact local: `runs/modal-cpu-1793514027877932400/`.

Function dùng 1 CPU/512 MiB, max container 1, timeout 120s/startup 300s/retries 0. Kết quả 2 câu, 0 lỗi; request `https://example.com` thất bại với URLError dưới policy chặn egress. Thời gian trong function khoảng **0.539s**, bao gồm network probe và smoke; không phải cold-start tổng hoặc benchmark model. App báo completed. Không dùng GPU, không tải weights, không gửi dữ liệu BTC.

`remote_summary.json` lưu hash từng artifact và hash infra source; `manifest.json` lưu core/config/fixture/lock/runtime hashes. Image không có Git nên commit/dirty/diff để null thay vì bịa commit; source hashes vẫn có. GPU/PA được ghi chưa đánh giá. Chi phí billing thực tế chưa được trả về; cần xem usage/dashboard, không báo 0 USD.

Hai lần trước chưa qua: lần 1 lock bị coi là thay đổi vì mirror index của Modal; đã ép index giống local và giữ `--locked`. Lần 2 image không có executable Git; đã sửa manifest chịu được môi trường đóng gói thiếu Git và thêm regression test. Lần 3 thành công; log lần 2/3 giữ trong `runs/`. Không bật retry tự động.

## Tái tạo và giới hạn

Core dependencies đã sync trong image Linux từ cùng lock và chạy offline smoke. Môi trường core sạch local `.tools/repro-venv` đã được tạo bằng `UV_PROJECT_ENVIRONMENT=.tools/repro-venv` với `uv sync --locked --offline --no-dev --no-group cloud`: exit 0, 8 package core cài lại, import pass và smoke pass (`runs/smoke-20261101T062155Z-dd02178e/`). Không dựa vào package cloud/dev của `.venv` cũ.

Kiểm tra checksum artifact tải từ Linux phát hiện text mode Windows tự đổi LF thành CRLF. Đã sửa writer tải về dùng UTF-8 bytes và khôi phục đúng LF cho artifact hiện có chỉ khi hash chuẩn khớp. Kiểm tra lại đủ 8 file khớp SHA-256 từ remote. Writer local này và pin build backend Hatchling 1.33.0 được bổ sung sau lần cloud thành công; hashes trong remote summary giữ nguyên bản đã chạy, không sửa lịch sử. Pin Hatchling lấy từ bản thực dùng trong build cache local; core dependency lock không đổi.

Chưa có scorer/runner/Docker guide BTC để hoàn thành P00. Chưa khóa split nội bộ hoặc nghiên cứu nhãn. Chưa xác minh upstream revision, quyền upload raw, quota GPU, billing/spend cap hoặc backup kit ngoài ổ D. Dockerfile là ứng viên, base version pin theo tag; OCI digest/full Docker còn chờ nghiệm thu. Smoke fake không chứng minh model hiểu tiếng Việt/SQL hoặc tăng PA.

Việc tiếp theo: hoàn thành P00 từ artifact chính thức, rồi khóa split P01 trước phân tích sâu câu/nhãn.
