# P00 — Đối chiếu contract ban đầu

Nguồn đã đọc: `Thể lệ cuộc thi/The_Le_Zalo_AI_Challenge_2026_DataMate.docx` được người dùng cung cấp, và cấu trúc kit local. SHA-256 được lưu trong `manifests/kit_files.json`. File DOCX tự mô tả là tài liệu tổng hợp; chưa xác minh revision hoặc changelog với cổng BTC. Các con số dưới đây là nội dung tài liệu được cung cấp, không phải xác nhận mới từ website BTC.

| Yêu cầu theo tài liệu | Nguồn | Cách kiểm tra / trạng thái |
|---|---|---|
| Question có `id`, `business_id`, `question`, `as_of_date` | §1 và ví dụ input; quan sát questions train | Validator có; 3.000 câu train đọc được. Chưa nghiên cứu nội dung nhãn |
| Data split có `data/<business_id>/`, rulebook, calendar, questions; chỉ train có answers | §3.2 | Kit local có train/public_test; hash toàn bộ file |
| 9 kiểu output: number, percent, string, date, boolean, list, table, unanswerable, abstain | §1, §2.1, §3.5 | Structural validator; matching/scorer chưa có |
| Submission mỗi dòng JSON gồm id/type, answer theo kiểu; reason tùy chọn | §3.5 | Stub ghi đúng hình dạng `id/type=abstain`; không thêm alias |
| Missing answer là abstain; PA = (correct − wrong)/N | §2.1–2.3 | Chưa có scorer gốc; không báo PA từ smoke |
| `predict.sh` đọc `/data`, ghi `/result/submission.jsonl` | §3.5 | Entrypoint stub đã có; chưa nghiệm thu bằng runner/Docker BTC |
| Log từng câu dưới `/result/logs/`: ID, final answer, thời gian, code/kết quả thực thi | §3.5 | Stub log ID/answer/time và ghi rõ không thực thi model; smoke lưu SQL/results |
| `/data` read-only; temp ghi nơi khác; inference hoàn toàn offline | §4, mục 3 và 5 | Code không sửa input; cloud synthetic có probe chặn egress. Full Docker còn chờ |
| Tổng mọi model inference ≤15B, tính toàn bộ MoE; weights công khai trước 01/10/2026 và license hợp lệ | §4, mục 2 | Chưa chọn model; kê khai ở `manifests/models.json`; đối chiếu hiện hành ở P04 |
| Không human-in-loop/hard-code ID; không dùng public/private test để training | §4, mục 4 và 6 | Fake chỉ synthetic, stub abstain mọi câu; chưa dùng test để train/tuning |
| Máy chấm: 2×RTX 5090 32 GB, RAM 512 GB; toàn job ≤6 giờ gồm load | §4, mục 7 | Chưa xác minh Docker guide hoặc đo GPU; P04/P13 |
| Re-run lệch PA không quá 0.03 | §4, mục 8 | Chưa đánh giá |
| Hạn Docker 23:59 ngày 16/11/2026, GMT+7 | §5 | Cần đối chiếu thông báo BTC mới nhất trước khi chốt lịch |

## Quan sát kit

Train: 30 business directories, 162 file, 194.290.513 bytes; 3.000 câu hỏi được kiểm tra format qua stub. Public test: 14 business directories, 97 file, 109.361.117 bytes. Chỉ kiểm kê metadata/hash ở bước này; chưa nghiên cứu đáp án hoặc dùng public test để điều chỉnh giải pháp.

Chưa thấy evaluator/scorer, runner mẫu, Docker guide, predict mẫu hoặc manifest phiên bản trong workspace. Điều đó không chứng minh BTC không cung cấp; cần bổ sung từ nguồn hiện hành. Không tự thiết kế scorer rồi gọi là chính thức.

## Giới hạn triển khai

Schema question dựa trên file train hiện có. Kiểm tra hình dạng đáp án không xác nhận toàn bộ semantics matching, đặc biệt rounding/alias/table order. Stub hiện chỉ kiểm tra wiring, chưa được scorer gốc chấp nhận và không phải B0. `predict.sh` sẽ được thay bằng pipeline thật ở P05. Rulebook phải lấy đúng split; không chép luật train vào code inference.
