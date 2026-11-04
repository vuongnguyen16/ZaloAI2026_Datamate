# Foundation kế thừa cho Timeline A–G

Bản ghi gọn thay các báo cáo tiến độ theo roadmap đã bỏ. Ngày tổng hợp 04/11/2026.
Các con số dưới đây là lịch sử đã ghi nhận, không phải phép đo mới trong reset.

## A — Inventory cơ học

Code `scripts/inventory.py`, test `tests/integration/test_inventory.py`.
Đã xử lý output trong input/alias/junction, JSON strict, ID nguyên văn và cách
đếm câu hợp lệ. Regression tiếp tục giữ, không thay expected hành vi.
Inventory train ngày 01/11: 30 business, 3.000 câu, 162 file, 194.290.513 bytes,
một nhóm bảng trùng hash, không lỗi cơ học. Artifact:
`runs/p01-inventory-fixed-20261101/inventory.json` và `inventory.md` (local).
Chưa đọc dòng/cột nội bộ, sheet/header/SQLite catalog hoặc README nội dung;
chưa loader, profile hoặc split. Bảng trùng byte chưa chứng minh business trùng.

## E/G — Contract, runner và bằng chứng

Strict parser/schema/validation trong `src/datamate/`, cùng CLI smoke/stub.
Contract nguồn tại `docs/requirements.md`, `manifests/competition_contract.json`
và `manifests/contract_sources.json`; raw hash ở `manifests/kit_files.json`.
Kiểm tra cấu trúc ngày 01/11 đã bao phủ train 3.000 câu/30 business và public
1.000 câu/14 business: output/log đủ ID, không trùng/ngoài input; mọi output
abstain. Bản JSON lịch sử: `reports/contract_checks.json` (giữ payload gốc).
Không parse gold; không tính PA; không coi stub là baseline.
`scripts/verify_contract.py` là lệnh tái hiện với tên hiện tại; các đường dẫn
run lịch sử giữ nguyên để không sửa lịch sử artifact.

Cổng CPU trước reset gần nhất: 58 tests pass trong 12.04s, Ruff/format pass.
Artifact `runs/cpu-check-20261104T162620562569Z-1s4dntg2/gate.json`.
CPU gate hiện lưu command/exit code/log/hash/runtime, dừng lỗi đầu, loại test
GPU/Modal, từ chối pass khi source đổi; CI synthetic chưa chạy trên GitHub.

## D/G — Modal và môi trường

CPython 3.11.18, uv 0.13.6, dependencies từ uv.lock; core không import Modal SDK.
Ngân sách được giao 30 USD/thí nghiệm, profile/workspace `vuonghungnguyen07`.
Xác thực và smoke cloud CPU đã chạy ngày 01/11, cần kiểm tra lại trước job mới.
App lịch sử: `ap-V5mZIojkntGhLow7r8ahUW`; image `im-aw8AXx4XzPdherlbygTxUN`.
Artifact `runs/modal-cpu-1793514027877932400/`; app đã completed theo report cũ.
1 CPU/512 MiB, tối đa một container, timeout 120s/startup 300s/retries 0;
block_network, outbound request thất bại; hai câu synthetic đúng, không lỗi.
Function khoảng 0.539s gồm probe/smoke, không là cold-start hay benchmark model.
Tám file tải về đã được kiểm tra SHA-256 sau xử lý LF/CRLF trong phiên trước.
Không GPU/weights/BTC upload; billing thực tế và hard spending cap chưa đo.

Dockerfile/.dockerignore giữ nguyên bản nháp; chưa nghiệm thu container.
Những module còn thiếu phải nghiệm thu theo task A–G mới, không chuyển các
trạng thái done của roadmap cũ thành bằng chứng hoàn thành timeline.
