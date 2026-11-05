# Đồng bộ lộ trình một người theo giai đoạn

Ngày 05/11/2026. Người dùng yêu cầu đồng bộ workspace/GitHub theo DOCX mới,
lưu phần cũ trên GitHub rồi dọn workspace. Đây là phạm vi migration tài liệu,
tracker và harness; không triển khai P0 hoặc khởi chạy model.

Nguồn hiện hành: `Research/Timeline DataMate theo nhóm việc A–G.docx`, SHA-256
`b70f5e852b156c7ff0835eebbdd96ccb71b718fd095fd797b554efe5b1837219`.
Đã đọc toàn bộ đoạn văn, bảng và quan hệ ảnh/link OOXML. Nguồn mô tả công việc,
không chứng minh module, model hay kết quả nghiên cứu đã được xác minh.

Giả thuyết: thay dependency theo P0–P9, gắn tracker/bản web vào hash DOCX và
từ chối readiness khi lệch nguồn sẽ ngăn phiên tiếp theo dùng nhầm kế hoạch.

| Phương án | Quyết định và lý do |
|---|---|
| Giữ tracker tuần T1–T8 bên cạnh tracker pha | Loại: tạo hai đường triển khai; model có thể mở trước split |
| Xóa foundation A-T1/A-T2 | Loại: DOCX yêu cầu giữ; đã có code và evidence |
| Giữ foundation, thay tracker pha, archive tài liệu lỗi thời trên GitHub | Chọn: một nguồn kế hoạch và một registry task |

Kiến trúc mục tiêu chuyển thành domain_lib dựng từ dev, model nhỏ gọi hàm,
SQL/Python dự phòng. Migration chỉ ghi scope/acceptance; P2 phải có spec và
thử nghiệm riêng trước khi thay runtime. single_sql giữ làm đối chứng.

Các quyết định áp dụng:

- A-T1/A-T2 giữ done với bằng chứng lịch sử và giới hạn; actual descriptor trong
  prompt và PA từ D-E-T2 chuyển vào P2, không bị xóa.
- P0 khóa nhóm business/template và access policy trước taxonomy có gold.
  Taxonomy toàn train không được tiết lộ gold holdout cho người chọn cấu hình:
  dev được phân tích chi tiết; calibration/holdout chỉ qua evaluator theo policy
  đã khóa. Gold holdout chỉ mở cho đánh giá P7, không dùng viết hàm/prompt.
- P0 gồm scorer, split, taxonomy và G0; P1 chỉ mở khi G0 done. Các pha sau
  tuần tự; P8a/P8b cần quyết định chạy hoặc bỏ có lý do trước P9.
- Docker thuộc G tại P3, sau lát cắt xuyên suốt P2. Điều này cụ thể hóa lại
  "sau pipeline hoàn chỉnh": không chờ tối ưu P4–P8. Giữ draft trong migration.
- DOCX có câu yêu cầu duyệt tracker; yêu cầu trực tiếp trong phiên này đã
  cho phép cập nhật. Các câu về quyền dữ liệu/AI trong DOCX không tự cấp quyền
  upload trong phiên này. Không upload dữ liệu BTC lên GitHub; job Modal sau
  phải xác minh account, budget và phạm vi dữ liệu trước khi chạy.
- Mốc BTC, model card, sm_120/proxy và kết quả paper trong DOCX là nguồn để
  xác minh tại task liên quan; migration không biến chúng thành contract.
- X12 ở sổ thí nghiệm là tính tất định; F2 cũng dẫn X12 cho SFT/RL, là tham
  chiếu chưa nhất quán của nguồn. P8B dùng so sánh F2 riêng, không ghi đè X12.
- Các ngưỡng ≥95%, sai ≤10%, ΔPA≤0,01 là mục tiêu nội bộ, không đổi luật BTC.

Archive đã push trước khi dọn:
[archive/timeline-20261103](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/tree/archive/timeline-20261103),
trỏ commit `bd0061593698df76c05745c7ef1df3d31b1331f3`.
Chỉ dùng tra lịch sử; không phục hồi làm nguồn kế hoạch.

Phép thử: DOCX→Markdown giữ đủ text/bảng/link/ảnh; bản web/asset/registry/hash
phải khớp; task không trùng ID, dependency không thiếu/vòng lặp, tối đa một
task in_progress; nguồn lệch hoặc dependency lỗi phải chặn readiness. Giữ
regression raw/schema/CPU, chạy CPU gate mới và đọc log. Kiểm diff, UTF-8/NFC,
link nội bộ và SHA remote; dữ liệu/kit manifest/config/Docker phải giữ nguyên.
Review do tác giả thực hiện, không phải review độc lập.
