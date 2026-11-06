# Khảo sát CPU và phạm vi P2c

Ngày 07/11/2026; increment thuộc P2 đang active, sau runtime PR #3.
Đây là kế hoạch khảo sát, không mở task hoặc thay timeline/G2.

**Nguồn:** yêu cầu người dùng; timeline hiện hành; split/access P0;
taxonomy đóng băng; rulebook dev. **Giả thuyết:** hai họ tổng doanh thu và
đếm đơn có thể tạo lát cắt bảo thủ; số ô taxonomy chưa chứng minh độ phủ.

**Cách làm:** nghiên cứu CPU local, không sửa inference/scorer/access policy.
Không đọc calibration/holdout gold. Script và mọi record BTC giữ local trong
`.tmp/`/`runs/`. Chỉ đưa kết luận, định nghĩa và locator nguồn vào tài liệu.
Phương án đọc toàn bộ gold dev bị loại: chỉ cần tối đa40 record đã chọn trước.

- [ ] Xác minh taxonomy/hash/split; phân loại 405 câu bằng nội dung câu hỏi:
  dấu hiệu lọc, một/nhiều kỳ, độ hạt. Có bucket mơ hồ; không gọi heuristic
  là eligibility hoặc độ phủ. Không dùng gold để phân loại câu hỏi.
- [ ] Chọn tối đa10 câu/cụm, phân tầng dạng kỳ và hai họ number/percent;
  khóa danh sách trước khi đọc gold. Authorize dev gold rồi chỉ route/decode
  tập con đó bằng scoped reader, ghi audit và kiểm nguồn không đổi.
  Báo dạng số/độ lớn tổng hợp; không suy quy tắc từ mẫu nhỏ.
- [ ] Checklist rulebook: ngày, trạng thái, grain, trả hàng, chiết khấu,
  VAT/phí ship, as_of_date, kỳ so sánh, làm tròn, mẫu số và dữ liệu thiếu.
- [ ] Viết `p2c_domain_scope.md`: hai hàm chính, percent tùy chọn; unknown
  filter abstain, không lọc bỏ im lặng; precision>=90% trên>=2cụm, mỗi cụm
  >=15 câu đã trả lời; chưa đủ mẫu không đạt. Không thay G2 toàn dev.

**Phép kiểm:** synthetic kiểm phân loại/routing tập con, selected trước gold;
hash manifest/taxonomy/rulebook, audit decode ngoài dev=0; số ô=405 và tối đa40
gold mẫu; QA UTF-8 và chỉ diff tài liệu phù hợp. Chưa đo PA hoặc chạy model.
Sau khảo sát mới phác prompt/cache và chuẩn bị probe P2b; account/budget phải
được xác minh lại trước GPU. Không coi credit xác nhận ở P1 là số hiện tại.
