# P2c: khả năng đủ mẫu đếm đơn và phản biện bước tiếp — 08/11/2026

Nguồn: phản hồi người dùng sau `d5c9ea2`; timeline/hash hiện hành,
`p2c_domain_scope.md`, `p2_g2_g5_decisions.md`, rulebook L10/L14/L110,
scoped question reader, audit sau lexicon và core `orders/metrics`.
Đây là assessment của increment P2, không mở task hoặc roadmap khác.

## Quyết định và phép thử

1. Merge PR#7 sau khi xác minh CI đúng head, job log, mergeability và review
   thread; người dùng đã cho phép merge khi xanh. Không merge thay đổi mới.
2. Đếm câu hỏi theo text, chỉ decode1895dev bằng `read_scoped(...questions)`.
   Dùng classifier hiện hành với expected_type cố định không phải gold;
   không chạy `run_taxonomy` vì lệnh đó còn mở gold type. Tách inventory thô
   khỏi phạm vi đếm đơn mặc định/unfiltered, đọc lại text các bucket và kiểm
   tín hiệu bị bỏ sót. Bảng theo business/member/ID và câu hỏi giữ local.
3. Không xem203nhãn heuristic/217tín hiệu là câu đã trả lời. So mẫu ứng viên
   với15 chỉ là phép thử khả năng, không cấp capability, precision hoặc PA.
4. Giữ ba tầng: binding đã kiểm ở>=2cụm là prerequisite; acceptance PA nội bộ
   **từng hàm** cần>=15answered/cụm, precision>=90% ở>=2cụm; G2 toàn dev cần
   PA>0, sai/answered<=10%, đủ output/log và báo coverage, không thêm cổng độ
   phủ. Không gộp revenue để tuyên bố order_count đủ mẫu; không sửa acceptance.
5. Bước eligibility nhị phân chỉ xem lại proposal. L10/L14 loại huỷ/trả;
   L110 đóng canonical lifecycle ở4trạng thái. Không nhận ra cách viết của
   nhãn không chứng minh nó bị loại. Không thêm trạng thái thứ5 vào core
   hoặc đổi6unknown đã duyệt. Một đề xuất có nghĩa trả có thể dùng returned
   hiện hữu sau phê duyệt mới;5nhãn còn lại vẫn có thể được tính.
6. Author review23nguồn theo metric **và scope unfiltered**, có role/rationale/
   source span, không chỉ basename. Giữ các nguồn có thể chứa trả hàng hoặc
   allocation chưa rõ ở required-review, không loại. Proposal không thay
   receipt người dùng hoặc kiểm CPU parse/cardinality/completeness.

## Kết luận định hướng

Phép thử text cho thấy nguồn-only không tự tạo đủ mẫu cho acceptance hiện tại:
C2 có3ứng viên mặc định, C3 có12; business đã bind ởC4 có8. Giải trạng thái
ở nhóm status-only có thể bổ sung21ứng viên C1 và11ứng viên C4, nhưng phụ
thuộc nghĩa nhãn tích cực/đang giao; đổi mọi nhãn lạ thành không tính là sai.
Không suy từ trung bình số câu/business hoặc7business sang>=15answered/cụm.

Giữ ưu tiên order_count và duyệt nguồn để mở cụm, nhưng tiếp tục parser/
throughput/predict chỉ với capabilities được CPU/human xác nhận. Nếu thiếu
mẫu, mở rộng bindings hoặc scope có chứng minh; không tự hạ acceptance và
không chuyển P3 lên trước G2. Revenue vẫn có bằng chứng và acceptance riêng.
