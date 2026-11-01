# Những mục cần xác minh

1. Revision/changelog của kit và thể lệ trên cổng BTC; deadline hiện hành có thay đổi không?
2. Evaluator/scorer, runner chính thức và Docker guide nằm ở đâu? Cần chúng để hoàn thành cổng P00/P02.
3. `/data` mount trực tiếp split hay có wrapper; entrypoint, quyền user, Docker base/CUDA chính thức, cache/temp/resource constraints cụ thể?
4. Các corner case của serializer/scorer: rounding tie, table cells/nulls/column fallback, alias, duplicate/unknown IDs? Không sửa scorer dựa vào suy đoán.
5. Quyền upload dữ liệu BTC lên Modal hoặc dịch vụ AI coding và quyền phân phối lại kit? Hiện chỉ synthetic được gửi Modal; raw/labels không push.
6. GPU/quota/credits và spend limit dashboard của workspace `vuonghungnguyen07`? Ngân sách người dùng cho phép là 30 USD/thí nghiệm; chưa biết billing thực đo.
7. Máy cloud nào dùng nghiệm thu Docker tương đương BTC? Modal Function chặn egress chưa thay thế Docker `/data` read-only trên máy chấm.
8. Nơi backup kit và artifacts lớn ngoài ổ D/Volume; thời gian tập trung còn lại của người phát triển?
