# Những mục còn cần xác minh theo A–G

- A: format/schema thực tế, header/encoding/dirty patterns; inventory cơ học
  chưa trả lời các câu này. Revision/changelog kit chưa rõ.
- E: chưa có scorer của dự án. BTC không cung cấp executable evaluator theo xác
  nhận của người dùng; xây matching từ thể lệ, ghi policy provisional cho rounding
  ties, alias, table order/null/cell và trường hợp đặc tả chưa rõ.
- E: split/access policy trước tuning/huấn luyện; không chọn cấu hình trên
  holdout hoặc public/private test. Chưa có manifest split đã khóa.
- C: rulebook/checklist và calendar semantics phải được nghiên cứu trực tiếp;
  không lấy giả định của timeline làm định nghĩa chính thức.
- D/G/F: quyền gửi BTC data lên Modal, quota GPU, usage/billing/spend cap chưa
  được xác minh. Chỉ synthetic đã được gửi cloud; budget 30 USD/thí nghiệm.
- G: offline/mount/quyền/temp/cache, cold start/full runtime và Docker digest
  chưa kiểm chứng. Chờ pipeline hoàn chỉnh để đóng gói, không chặn việc CPU sớm.
- Nguồn lịch trong contract được đối chiếu 01/11; timeline DOCX có mốc ước tính
  khác. Khi lập lịch/nộp phải xác minh BTC hiện hành, không tự coi ngày trong
  tài liệu kế hoạch là deadline BTC đã xác nhận.
- Backup raw/artifact ngoài ổ D chưa xác minh. Backup cleanup trong runs chỉ
  bảo vệ 32 file code/tài liệu bị đổi, không thay thế bản sao lưu kit.
