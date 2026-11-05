# P0-SPLIT thiết kế khóa split và quyền truy cập

Ngày 05/11/2026. Scope: tạo split train có provenance/hash, kiểm rò rỉ theo
business/template/file, access policy và giao thức thống kê/leaderboard.
Không xây scorer/taxonomy, không đọc gold, không chạy model hoặc cloud.

Nguồn: Timeline DOCX hiện hành §4/P0, §5/E3, §8 (hash trong timeline registry),
contract `docs/requirements.md`, code loader và A-T2 `labels_frozen.json` có
SHA-256 `3eb90b23bf13b185559a4d1a87f7c6a932044d0e654b2410c3e66d24d8815ef6`.
A-T2 có 322 CSV/XLSX unit, 80 nhóm header/file; partition dev/check cũ chỉ
để nghiên cứu cấu trúc, không được tái dùng làm QA split. Metadata SQLite
đọc catalog/schema, không đọc cell. Câu hỏi chỉ dùng ID/business cho membership.

Quan sát trước chọn split: A-T2 nối thành 17 cụm trong 29 business CSV/XLSX.
Thêm business SQLite và nối README layout preamble giống nhau cho 9 cụm
business toàn train. Không dùng gold, kết quả model hay PA để chọn nhóm/seed.
README mô tả bố cục, không có taxonomy ngành được xác nhận. Không coi layout
holdout là bằng chứng chưa từng gặp ngành kinh doanh.

Giả thuyết: nối bắc cầu tất cả shared full-header template, file byte-identical
và README layout, rồi phân cả cụm, sẽ tránh train/calibration/holdout có cùng
template đã nhận diện. Preamble normalize NFC/casefold/whitespace; giữ nguyên
giá trị nguồn. Header template của SQLite dùng cùng cách normalize grid A-T2.

| Phương án | Kết luận |
|---|---|
| Random từng câu 60/20/20 | Loại: cùng business/template ở nhiều partition |
| Random business bỏ liên kết template | Loại: cùng khuôn nguồn có thể rò rỉ |
| Chia theo cụm bắc cầu, seed cố định, tối ưu tỷ lệ theo business | Chọn; công bố tỷ lệ câu hỏi và giới hạn số cụm |

Thuật toán khóa trước khi chạy: thứ tự cụm bằng SHA(seed, members); quy hoạch
động tối thiểu độ lệch tuyệt đối số business so với 60/20/20, mỗi partition
không rỗng. Trong các phương án cùng tỷ lệ, ưu tiên holdout nhiều/hiếm layout
dựa trên tần suất preamble và đa dạng định dạng; hòa thì hash assignment.
Không thử nhiều seed hoặc chọn lại bằng điểm. Không tách cụm để ép đúng tỷ lệ.
Giới hạn CPU ≤200 business; không dò tổ hợp vô hạn. Nếu dưới 3 cụm thì fail.

Artifacts thật chỉ ở `runs/`, không copy/chia lại `data/`: manifest chứa file
hash, question membership, lý do/edge nhóm, policy/source hash; lock tham chiếu
manifest hash và policy hash. Xuất bản code/config/doc với fixture synthetic.
Kiểm tra nguồn/hash/coverage trước dùng; output mới/disjoint input, chống alias,
không ghi đè split cũ. Chạy lại cùng source/policy phải ra manifest bytes giống.

Quyền ứng dụng: dev cho phát triển/taxonomy/huấn luyện được phép; calibration
chỉ evaluator chọn ngưỡng/kiểm tối ưu, không xuất gold để viết hàm; holdout gold
từ chối trong P0, chỉ có giao thức release một lần tại P7 qua evaluator với
predictions/config đã đóng băng và ledger. Không có lệnh unlock trong increment
này. Public/private không dùng tuning. Guard là kiểm soát của API project,
không phải mã hóa/ACL chống người dùng đọc trực tiếp file cùng tài khoản.
Inference không có nhu cầu gold. Không thêm gold loader trong P0-SPLIT.

Ledger khởi tạo rỗng, hash-chain và exclusive lock cho access audit và nhật ký
public. Ghi mục đích, partition/resource, fingerprint ứng viên; không ghi answer.
Nhật ký public chỉ cho format/crash/generalization, tối đa một lượt mỗi pha
theo policy nội bộ; quota BTC phải xác minh khi nộp, không tự gửi submission.

Thống kê khóa ở policy: PA theo câu; ΔPA candidate-control ghép cặp cùng ID,
lấy mẫu cụm business với hoàn lại ≥1000 lần, CI percentile 95%, seed cố định.
Vì template tạo phụ thuộc giữa business, báo thêm bootstrap theo cụm leakage
đã khóa và số cụm thực tế; không khẳng định ý nghĩa khi quá ít cụm. Dùng dev
cho quyết định kỹ thuật; calibration cho ngưỡng; holdout chỉ audit một lần.
P0-SCORER sẽ triển khai thống kê/matching; increment này chỉ khóa giao thức.

Phép thử: fixture nối bắc cầu/đảo thứ tự/determinism, duplicate/missing ID,
label stale hoặc thiếu coverage, nguồn/output alias, raw mutation, manifest/
policy tampering, cấm gold inference/holdout, ledger corruption và ghi trùng
public. Thực chạy toàn train/repeat và audit độc lập membership/edge/hash;
CPU gate mới, không dùng PA hoặc fake làm quality evidence. Review self-review.
