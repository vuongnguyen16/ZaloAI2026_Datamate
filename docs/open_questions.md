# Quyết định đã khóa và những điểm cần xác minh

Ngày06/11/2026, chủ project xác nhận phạm vi P2: input/câu hỏi dev và
artifact tối thiểu của dev được dùng trên Modal, gồm prompt/descriptor cho
probe thật. Không đưa gold calibration/holdout lên cloud; gold không vào
inference. Gold dev chấm local qua scoped evaluator. Quyền này không mở API
ngoài Modal hoặc publish dữ liệu lên GitHub; trước mỗi job vẫn kiểm account,
workspace và budget30USD. Không hỏi lại cùng quyền Modal đã ghi nhận.

[Quyết định G2/G5](research/p2_g2_g5_decisions.md) đã chốt theo xác nhận mới
của người dùng, thay lựa chọn giữ dự thảo trước đó. G5 dùng ngưỡng kỹ thuật
và dung sai điểm ròng từng cụm trong [policy](../configs/g5_decision_policy.json);
hai khoảng CI chỉ mô tả. Đây là contract cho P5, chưa phải runtime đã triển khai.

- P0: matching corner cases từ thể lệ; phần chưa rõ gắn provisional. Khóa nhóm
  business/template và access policy trước khi đọc gold; taxonomy holdout không
  làm nguồn chọn cấu hình. Split đã khóa theo [P0-SPLIT](split_policy.md);
  scorer đã có [policy provisional](evaluation.md). Holdout có 2 cụm độc lập,
  cần nêu giới hạn thống kê; chưa model/B0.
- P1: model card/revision/license/cutoff/tổng tham số, runtime và proxy sm_120;
  không coi danh sách ứng viên trong DOCX là eligibility đã xác minh.
- Mọi job P1/P2/P8b: account/quota/usage/billing, budget30USD/thí nghiệm và
  scope dữ liệu cụ thể. Quyền P2 ở trên đã ghi nhận; migration lịch sử không
  tự upload. Không upload kit/gold lên GitHub/API ngoài Modal.
- P2/P4: rulebook/calendar semantics có nguồn; 38 status từ khảo sát là giả thuyết,
  không tự trở thành mapping production. Chưa domain_lib, cleaner hay baseline.
- P3: offline/mount/read-only/cache, cold start/tail/full runtime và digest;
  đóng gói sau G2, không chờ P4–P8.
- P7/P8: holdout mở một lần; nếu tiếp tục tối ưu sau P7 phải có đánh giá độc lập
  mới hoặc công bố giới hạn, không tái dùng holdout làm unseen test.
- Nguồn có hai cách dùng X12: sổ thí nghiệm dành cho tất định, F2 dẫn cho SFT/RL.
  P8B ghi control riêng, không thay X12. Ngưỡng đề xuất trong kế hoạch là mục tiêu nội bộ.
- Lịch/quota nộp cần xác minh BTC lúc nộp; backup kit ngoài ổ D chưa xác minh.
