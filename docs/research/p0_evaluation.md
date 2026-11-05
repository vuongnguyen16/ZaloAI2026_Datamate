# Hoàn tất P0 scorer taxonomy và G0

Ngày 05/11/2026. Người dùng yêu cầu hoàn tất P0; triển khai tuần tự P0-SCORER,
P0-TAXONOMY, P0-GATE. Không mở P1, model/Modal/Docker hoặc nộp public.

Nguồn: Timeline hiện hành §4/P0, §5/E1–E3, §8; split lock/policy đã khóa;
DOCX thể lệ `Thể lệ cuộc thi/The_Le_Zalo_AI_Challenge_2026_DataMate.docx`,
SHA-256 `9d28162bbe2ddcc6373279bc29935c7899f05bb5e736f631de06a4beb19b782e`.
Đã đọc đoạn văn và bảng OOXML. Locator dùng body paragraph/table index từ 0:
§2.1 paragraph12 và table2 (matching), §2.3 table3 (PA), §3.2 paragraph24
(answers/alias). Không có executable BTC; không tuyên bố project scorer trùng
BTC ở những chỗ nguồn chưa xác định.

Giả thuyết: matching tất định có policy/source hash, reader giải mã riêng phần
được phép và phép kiểm synthetic/corner case đủ sẽ tạo cổng G0 dùng được cho
P1/P2 mà không cần model hoặc xem gold holdout.

| Phương án | Quyết định |
|---|---|
| Parse toàn answers.jsonl rồi lọc | Loại: giải mã gold holdout trước P7 |
| Tách/copy lại dữ liệu gốc | Loại: sửa/nhân bản kit, khó giữ provenance |
| Stream byte, chiếu ID; chỉ JSON-decode record được phép | Chọn: file train chung vẫn được đọc byte để routing, nhưng không giải mã type/answer/alias ngoài scope |

Reader phải authorize trước khi mở file; ID scanner kiểm cấu trúc JSON bằng
byte, chỉ giải mã tên key cấp đầu và giá trị id, không giải mã các value khác.
Kiểm duplicate/unknown/missing ID trên toàn envelope, giới hạn dòng/depth/count.
Không coi đọc byte/ID là chưa mở file gold: audit ghi rõ routed IDs và các
record thực sự được giải mã. Holdout luôn từ chối, kể cả purpose P7. Access
ledger ghi request và parse completion/hash; API không thay OS ACL.

Matcher giữ luật nguồn: type phải đúng; missing/abstain=0, correct=+1,
wrong=−1, không partial credit. Number Decimal exact, không tự làm tròn prediction;
percent round2; string NFC→lower→non-alnum thành space→collapse, không bỏ dấu;
scalar string dùng alias được gold cung cấp; date ISO exact; boolean strict;
list positional; table reorder cột theo tên chuẩn hóa khi mapping đầy đủ duy
nhất, nếu không dùng vị trí; rows set. Không suy alias từ dữ liệu/ID nghiệp vụ.
Unknown/duplicate ID hoặc JSON không route được làm run invalid; answer sai
shape có ID hợp lệ tính wrong; type abstain luôn 0 theo nguồn, dù payload thừa.

Policy tạm bắt buộc công bố: percent ties HALF_UP, signed zero tương đương;
table mapping tên all-or-nothing, duplicate names fallback positional; numeric
cell không có tolerance; null cells không được schema hiện hành hỗ trợ;
alias chỉ scalar string, không tự gán alias lồng list/table. Thiếu đặc tả không
được gọi thành luật BTC đã xác nhận. Đóng băng policy trước mở gold dev.

run_eval đóng băng hash predictions/control trước đọc gold, scope dev hoặc
calibration evaluator. Report không ghi gold answer/alias; dev có log theo ID,
calibration chỉ xuất aggregate để không đưa lỗi từng câu vào vòng viết hàm.
Optional route/runtime phải là evidence thật; thiếu thì ghi unavailable.
Paired bootstrap cùng ID, ≥1000 lượt theo business và sensitivity leakage
component, seed/CI95 percentile từ split policy; không assert significance
với quá ít cụm. Có báo lỗi mới so control, theo type/business/route và taxonomy
khi có; scorer không là inference hoặc B0.

Taxonomy: chỉ dev được đọc question text và gold type; không dùng gold answer
để viết classifier. Rule heuristic theo họ chỉ số/operation/time/viết tắt,
có multi-label và unknown; không dựa business/question ID. Tổng coverage
3000 theo manifest, dev classified và calibration/holdout sealed báo riêng;
không mở gold 1105 câu ngoài dev để đạt đủ con số trong Timeline. Không dùng
taxonomy holdout để chọn cấu hình. Nhãn heuristic không phải human-reviewed.

Acceptance: fixture đúng/sai mọi type, precision Decimal/rounding/alias/list/
table/null, malformed/ID, reader không decode sentinel ngoài scope, deny
holdout/calibration developer, bootstrap determinism/cluster pairing, taxonomy
accents/time/ambiguity; CPU gate mới và provenance/raw/split hash giữ nguyên.
Chạy dev all-abstain chỉ là contract probe, không baseline model/PA chất lượng.
Review tự tác giả, không reviewer độc lập. Kết quả ghi reports/p0_results.md.

Schema inspection sau probe đầu: scalar-only alias validator dừng ở record
dev có nested aliases, chưa tính được PA. Dev có 65 list alias arrays khớp
từng vị trí (40 chứa strings và 25 arrays rỗng), 16 table alias arrays khớp
từng hàng, tất cả table đó có đúng hai cột (text, integer). Không xem giá trị
trong báo cáo schema, không giải mã calibration/holdout. Bổ sung policy tạm:
list aliases theo vị trí; table aliases cho text đầu hàng, matching song ánh
giữa các row set, không dùng một alias chung để che mất một hàng. Table nhiều
text column hoặc shape khác phải từ chối để nghiên cứu; không tự đoán. Đây là
schema compatibility từ dev, không chọn policy bằng điểm. Giữ bản freeze đầu
và freeze v2 riêng; không gọi nested alias semantics là BTC đã xác nhận.

Taxonomy v1 có 816/1895 câu `other`, chưa đủ định hướng P2. Đã rà 35 câu dev
`other` theo question-hash, chỉ đọc câu hỏi/type, không đọc answer. Mẫu thiếu
gồm dthu/bnhiu/hnay/hqua, telex typo và cách hỏi tiền/số đơn/đơn vị bán. V2 thêm
rewrite token và pattern tổng quát, ưu tiên chỉ số trước điều kiện hủy/trả,
giữ nhãn ambiguity/other. Không sửa theo business/ID, PA hoặc câu sealed.
Đây là heuristic dev, không phải contract parser nghiệp vụ cho inference.

Self-review bổ sung ca âm: không cho đưa raw `answers.jsonl` vào tham số
submission/policy/taxonomy/execution/rules để bypass scoped reader. External
input phải regular, không alias/hardlink và nằm ngoài raw/frozen split. Tham
số bootstrap và metadata được kiểm trước gold; read lỗi có progress audit.
