# A-T1 — Khảo sát đầu vào train

Ghi chép lịch sử của đợt khảo sát trước implementation. A-T1 hiện đã hoàn tất;
xem [nghiệm thu loader](../../reports/a_t1_loader_results.md),
[engineering A-T2](../../reports/a_t2_engineering_results.md) và state/backlog
để biết trạng thái hiện hành. Các mục còn mở bên dưới được giữ theo thời điểm khảo sát.

Đã có [khảo sát sâu bổ sung](a_t1_deep_survey.md): profile toàn cột, ngữ cảnh
nhóm, khóa nối và coverage. Số dòng lặp thô bên dưới là lịch sử của bước đầu;
không dùng thay số keyed/unkeyed đã phân biệt trong khảo sát sâu.

Ngày 05/11/2026, giờ Việt Nam. Phạm vi do người dùng giao: khảo sát train trước
khi triển khai loader. Nguồn kế hoạch là mục A/T1 trong
`Research/Timeline DataMate theo nhóm việc A–G.docx`, SHA-256
`e74b1292119f01ca3eae7d20d709921219efc30e655e01909685c50d5363eb51`.
Contract: `docs/requirements.md`, `manifests/competition_contract.json`;
ngữ nghĩa dữ liệu đối chiếu với rulebook và README local của train.

## Phạm vi đã khảo sát

- 30 business, 3.000 câu hỏi, 162 file raw, 194.290.513 bytes.
- 128 file bảng: 107 XLSX, 20 CSV, 1 SQLite; 30 README và 4 file cấp split.
- Đọc 302 sheet XLSX, 20 bảng CSV, 17 bảng SQLite; không lỗi đọc.
- 3.997.518 dòng có nội dung: CSV/XLSX bao gồm header, lời dẫn và dòng tổng;
  SQLite là COUNT(*) của bảng. Không gọi đây là số đơn/giao dịch.
- 17 XLSX nhiều sheet, tối đa 20 sheet/file. Không quan sát sheet ẩn, ô gộp,
  công thức hoặc ô lỗi Excel. CSV đều strict UTF-8 có BOM, dấu phẩy, chiều rộng
  dòng nhất quán trong từng file; chưa có bằng chứng TCVN3/VNI ở các CSV này.
- Câu hỏi có dấu/không dấu, viết tắt; 768 câu chỉ gồm ký tự ASCII.
  as_of_date từ 15/01/2025 đến 20/09/2026, không phải coverage bảng đã parse.
  7 business có 40 câu, 17 có 118, 6 có 119.
- Quan sát tiền/số/ngày trộn định dạng, header nhiều tầng hoặc ở dòng 4,
  bảng chia tháng/chia file, dòng tổng, số lượng kèm đơn vị và bản ghi lặp.
  README cho thấy độ hạt khác nhau: dòng hàng, hóa đơn, sổ không có mã đơn,
  phiếu thu, lô và chuyển động kho. Không suy khóa nối từ tên cột đơn thuần.
- Một nhóm file bảng trùng byte; không kết luận business trùng.

Không parse gold (`answers.jsonl` chỉ được hash nhị phân), không đọc nội dung
public/private, không tuning hoặc huấn luyện. Đầu vào toàn train đã được khảo
sát; ghi nhận mức truy cập này khi thiết kế split sau, không gọi holdout là
hoàn toàn chưa từng được xem. Chưa có quyết định kiến trúc hoặc thay contract.

## Bằng chứng và kiểm chứng

Chi tiết có ví dụ ô và thống kê từng business/file/sheet chỉ giữ local, bị Git
ignore tại `runs/a-t1-train-survey-20261105/`:

- `survey.py`, `survey.json`: khảo sát streaming bằng thư viện chuẩn Python;
  SQLite mở read-only/immutable, không chạy view/virtual table; không sửa input.
- `make_report.py`, `report.md`, `summary.json`: báo cáo và thống kê tổng hợp.
- `verify_survey.py`, `verification.json`: đếm độc lập token dòng XML trên 302
  sheet, CSV với delimiter cố định, danh sách file của 30 README; không issue.
- Hash trước/sau và hash kiểm tra lại của toàn bộ 162 file raw giống nhau.

Lệnh thực tế (cache/interpreter theo README):

```powershell
.tools/uv/uv.exe run --locked python scripts/harness.py context --task A-T1
.tools/uv/uv.exe run --locked python runs/a-t1-train-survey-20261105/survey.py
.tools/uv/uv.exe run --locked datamate validate-input --input data/train
.venv/Scripts/python.exe runs/a-t1-train-survey-20261105/verify_survey.py
.venv/Scripts/python.exe runs/a-t1-train-survey-20261105/make_report.py
.tools/uv/uv.exe run --locked python scripts/check.py
```

Các lệnh hoàn tất exit 0. Validator: valid=true, errors/warnings rỗng,
gold_content_read=false. CPU gate mới:
`runs/cpu-check-20261105T025942709843Z-6dd8b3eg/gate.json`: Ruff/format pass,
59 tests pass trong 8.87s, source_changed_during_gate=false. Đã đọc JSON và
ba log stage. Gate kiểm tra regression source nền, không chứng minh script
khảo sát local hay loader chưa có. Review: self-review; kiểm tra số đếm độc lập
trong cùng phiên, không phải independent agent review.

Sandbox local lỗi khởi tạo; các lệnh chạy bằng exec được cấp quyền ngoài
sandbox sau kiểm tra tự động. Không sửa dependency, source inference, data,
kit manifest hoặc gửi dữ liệu BTC lên Git/cloud. GPU/Modal model chưa chạy,
PA chưa đánh giá.

## Phần chưa nghiệm thu và hành động kế tiếp

Đã có bằng chứng cho phần khảo sát định dạng/dòng/cột/README. **A-T1 còn
in_progress**: chưa triển khai loader CSV/XLSX/SQLite → DuckDB, lỗi có cấu trúc,
cache/fingerprint theo business. Chưa làm profile null/min-max toàn cột,
cleaning hoặc xác minh join; các phần này cần increment tương ứng.

Hành động kế tiếp có giới hạn: trước khi build loader, ghi spec/research về
cách giữ raw, tọa độ/sheet/provenance, bảo toàn ID và lỗi đọc. Phân biệt giả
thuyết (đọc mọi ô thành raw value rồi tạo lớp phân tích riêng) với contract
đã xác nhận; so phương án với auto-inference và xác định phép thử bảo toàn
giá trị/số dòng trên fixture synthetic. Không tự triển khai ở phiên khảo sát.
