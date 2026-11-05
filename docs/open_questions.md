# Những điểm cần xác minh trước từng pha

- P0: matching corner cases từ thể lệ; phần chưa rõ gắn provisional. Khóa nhóm
  business/template và access policy trước khi đọc gold; taxonomy holdout không
  làm nguồn chọn cấu hình. Chưa scorer hoặc split manifest.
- P1: model card/revision/license/cutoff/tổng tham số, runtime và proxy sm_120;
  không coi danh sách ứng viên trong DOCX là eligibility đã xác minh.
- P1/P8b: account/quota/usage/billing, budget 30 USD/thí nghiệm và phạm vi dữ liệu.
  DOCX ghi chủ project cho phép dữ liệu BTC trên Modal; phiên migration không
  dùng câu đó để tự upload. Không upload kit/gold lên GitHub/API ngoài Modal.
- P2/P4: rulebook/calendar semantics có nguồn; 38 status từ khảo sát là giả thuyết,
  không tự trở thành mapping production. Chưa domain_lib, cleaner hay baseline.
- P3: offline/mount/read-only/cache, cold start/tail/full runtime và digest;
  đóng gói sau G2, không chờ P4–P8.
- P7/P8: holdout mở một lần; nếu tiếp tục tối ưu sau P7 phải có đánh giá độc lập
  mới hoặc công bố giới hạn, không tái dùng holdout làm unseen test.
- Nguồn có hai cách dùng X12: sổ thí nghiệm dành cho tất định, F2 dẫn cho SFT/RL.
  P8B ghi control riêng, không thay X12. Ngưỡng đề xuất trong kế hoạch là mục tiêu nội bộ.
- Lịch/quota nộp cần xác minh BTC lúc nộp; backup kit ngoài ổ D chưa xác minh.
