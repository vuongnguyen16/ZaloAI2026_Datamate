# Trạng thái DataMate theo Timeline A–G

Cập nhật 04/11/2026, giờ Việt Nam. Theo yêu cầu người dùng, timeline DOCX trong
Research là nguồn kế hoạch hiện tại; toàn bộ tracker cũ đã được thay thế.
Các mốc ngày trong DOCX là dự kiến, không tự thay lịch/contract BTC.

**Hiện tại:** đã dọn tài liệu cũ và giữ foundation có ích. Chưa bắt đầu build
task chức năng mới theo timeline. `G-FOUNDATION` và `A-INVENTORY` chỉ công nhận
phạm vi kế thừa, không tương đương G/T1 hay A/T1 hoàn thành.

**Đã có:** CPython 3.11.18 + uv 0.13.6 + lock; strict schema/validators;
fake/stub runner, logging/hash; inventory cơ học; CPU gate/CI; Modal CPU smoke
lịch sử. Xem `docs/foundation.md`. Chưa có real model, scorer, PA/B0.

**Kiểm chứng phiên reset:** cổng CPU chuẩn exit 0, Ruff/format pass và **59 tests
pass trong 12.07s**; artifact `runs/cpu-check-20261104T164734905777Z-5kmhmukp/gate.json`.
Context A-T1: todo/ready, timeline đúng hash, không warnings, CPU passed/current;
20 task không lỗi dependency/vòng lặp, ID cũ bị từ chối. Audit kit: hash train/public
và thể lệ giữ nguyên. Skill validator pass. Kết quả ở `reports/timeline_reset_results.md`.
GPU/model không chạy; PA chưa đánh giá. CI GitHub đã pass sau publish, xem phần
đồng bộ bên dưới. Review là self-review.

**Config/tài nguyên:** `configs/smoke.yaml` chỉ synthetic;
`configs/modal_dev.yaml` profile/workspace `vuonghungnguyen07`, tối đa 30 USD
mỗi thí nghiệm. Xác minh lại tài khoản/budget trước job. Không có model đã pin.

**Quy tắc tiếp tục giữ:** raw read-only; không đọc gold vào inference; không
upload BTC data khi chưa rõ quyền; không tuning bằng public/private test;
split/access policy phải rõ trước tuning/huấn luyện; model thật chỉ trên Modal.
Docker nháp giữ nguyên tới bước đóng gói nhóm G sau khi pipeline hoàn chỉnh.

**Bước tiếp theo:** A-T1 — khảo sát metadata dòng/cột/README và thiết kế loader
CSV/XLSX/SQLite → DuckDB giữ raw. Trước sửa đọc timeline A/T1 và contract; ghi
research/spec nhỏ, kiểm tra format thực tế được phép. E-T1 scorer và C-T1
rulebook/calendar vẫn todo; timeline ghi scorer “đã có” không phải bằng chứng
repo hiện có scorer. Không tự chọn/chạy model trong phiên cleanup.

**Phiên mới:** chạy `uv run --locked python scripts/harness.py context --task A-T1`,
đọc `read_first` và DOCX timeline, review diff rồi chạy CPU gate. Context trả
path/hash timeline; nếu thiếu thì báo thiếu, không hồi sinh plan đã bỏ.

**Backup:** `runs/timeline-reset-backup-20261104-233607/`, 32 file đã xác minh
SHA-256 trước sửa/xóa, local/ignored. Không xóa data, lịch sử Git, runs cũ,
môi trường uv hoặc tài liệu gốc; phiên cleanup không commit/push.

**Đồng bộ GitHub:** source/config/tests/tài liệu đã push lên repo public
`vuongnguyen16/ZaloAI2026_Datamate`, nhánh main, source commit `c69d4da`.
Đã đối chiếu remote SHA trùng local và CPU GitHub Actions run `41872674037`
completed/success. CPU local trước push: 59 passed in 7.49s, lint/format pass;
artifact `runs/cpu-check-20261104T165544622253Z-oze3s9zf/gate.json`.
Bản timeline Markdown giữ đủ 137 paragraph/15 bảng/123 dòng bảng và một sơ đồ,
có nguồn/hash DOCX. Dữ liệu BTC, credentials, model, runs và môi trường local
tiếp tục được ignore. Chi tiết ở `reports/github_publish.md`.
