# Những mục cần xác minh

1. Revision/changelog của kit local chưa rõ. Deadline giải pháp 23:59 ngày 16/11/2026 GMT+7 đã đối chiếu trang chủ BTC ngày 01/11/2026; vẫn kiểm tra lại trước freeze.
2. BTC không có runner/evaluator riêng, đã được người dùng xác nhận; không cần tiếp tục hỏi/tìm như blocker. P00 dùng đặc tả trong DOCX và validator project; P02 tự xây scorer từ đặc tả. Corner cases cần nghiên cứu được nêu ở mục 4.
3. `/data` mount trực tiếp split hay có wrapper; quyền user, Docker base/CUDA chính thức và cache/temp/resource constraints cụ thể? Theo quyết định chủ dự án, mọi việc Docker hoãn tới P13, không chặn P00–P12.
4. Các corner case của serializer/scorer: rounding tie, table cells/nulls/column fallback, alias, duplicate/unknown IDs? Không sửa scorer dựa vào suy đoán.
5. Quyền upload dữ liệu BTC lên Modal hoặc dịch vụ AI coding và quyền phân phối lại kit? Hiện chỉ synthetic được gửi Modal; raw/labels không push.
6. GPU/quota/credits và spend limit dashboard của workspace `vuonghungnguyen07`? Ngân sách người dùng cho phép là 30 USD/thí nghiệm; chưa biết billing thực đo.
7. P13 sẽ chọn host cloud nghiệm thu Docker tương đương BTC sau khi pipeline hoàn chỉnh. Modal Function chặn egress chưa thay thế Docker `/data` read-only trên máy chấm; đây là việc hoãn có chủ đích, không là blocker hiện tại.
8. Nơi backup kit và artifacts lớn ngoài ổ D/Volume; thời gian tập trung còn lại của người phát triển?
