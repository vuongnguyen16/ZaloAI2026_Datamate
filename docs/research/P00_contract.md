# P00 — Contract từ kit thật và nguồn BTC

Ngày kiểm tra 01/11/2026, giờ Việt Nam. Mục tiêu: chốt đầu vào/đầu ra và ràng buộc để làm P01–P05; không nghiên cứu nhãn, chọn model hoặc triển khai Docker.

## Bằng chứng

- **BTC xác nhận qua website công khai:** [DataMate Overview](https://challenge.zalo.ai/portal/datamate) mô tả package CSV/Excel/SQLite/README, câu hỏi tiếng Việt, as-of, rulebook/calendar và 9 kiểu output. JSON ví dụ có `id`, `business_id`, `question`, `as_of_date` và submission `id/type/answer`.
- **BTC xác nhận qua website công khai:** [Timeline](https://challenge.zalo.ai/#timeline) ghi nộp giải pháp 23:59 ngày 16/11/2026 GMT+7, private release 09:00 ngày 20/11 và nộp kết quả cuối 23:59 ngày 23/11. Trang chủ ghi kit/data/evaluation software được phát hành ngày 26/10; đó không phải bằng chứng chúng đã có đầy đủ trong thư mục local.
- **BTC xác nhận qua các tab công khai:** đã dùng TinyFish Automation mở Evaluation, Rule, Submission Guidance. Đối chiếu PA/type+value, giới hạn 15B gồm MoE, cutoff trước 01/10/2026, offline/read-only, 2 RTX 5090/512 GB/6 giờ, sai lệch PA ≤0.03 và quota nộp. Nguồn/giới hạn trong `manifests/p00_sources.json`. Exact predict.sh paths/logging vẫn căn cứ DOCX.
- **Tài liệu người dùng cung cấp:** `Thể lệ cuộc thi/The_Le_Zalo_AI_Challenge_2026_DataMate.docx` với section/paragraph trong `docs/requirements.md`; hash trong kit manifest. Đã kiểm tra lại thư mục, package embeddings và hyperlinks: chỉ có DOCX, không chứa executable hoặc link chấm.
- **Chủ dự án xác nhận:** BTC không cung cấp runner/evaluator riêng. Vì vậy triển khai công cụ project từ đặc tả; không để thiếu executable thành blocker hoặc điều kiện chờ. Phần Data cần đăng nhập không làm thay đổi cách triển khai này.
- **Quan sát từ kit:** 3.000 câu train và 1.000 câu public, schema nhất quán; tham chiếu lần lượt 30/14 business. Rulebook hai split có hash khác nhau, calendar có cùng hash. Validator chỉ đọc cấu trúc/câu hỏi/hash, không đọc gold hoặc nội dung bảng doanh nghiệp.
- **Quyết định người dùng:** Docker hoãn toàn bộ tới P13 sau khi pipeline hoàn chỉnh. Đọc và lưu contract filesystem/output vẫn thuộc P00; không chạy Docker hay sửa bản nháp Docker trong increment này.

## Lựa chọn và giới hạn

Chọn validator cấu trúc độc lập scorer: kiểm tra fields/date, business directory, rule/calendar, JSON strict, type/value, ID trùng/ngoài input, coverage và log. Phương án chỉ xem bằng mắt bỏ sót lỗi lặp/thiếu ID; triển khai matching/PA ở P00 sẽ trộn phạm vi P02. P02 xây scorer project từ quy tắc thành văn, không chờ code BTC.

Thiếu output được tính abstain theo tài liệu. Vì runner mong muốn xử lý đủ input, thêm policy `--require-complete` riêng; không gọi missing-ID là format sai của BTC. Unknown fields/type/value corner cases hiện theo schema nội bộ ghi trong code, chưa bảo đảm bao phủ mọi trường hợp evaluator chấp nhận.

JSON trùng key bị từ chối thay vì silently lấy key cuối; đây là policy phòng lỗi cấu trúc của project. Không hard-code business/question ID, không normalize câu trả lời hoặc tự đổi type để làm pass. Giới hạn 10.000 câu cho các phép thử này là guard CPU tạm, không phải giới hạn đề thi.

`predict.sh` giữ mặc định `/data` và `/result`, có override môi trường để thử shell trên máy hiện tại. Thử shell không chứng minh mount/quyền container. Stub tiếp tục xuất abstain, có giải thích không chạy model/tool; không được báo thành B0.

## Build và kiểm chứng

Module `src/datamate/validation.py`, strict JSON parser, CLI `validate-input`, `validate-submission`, `validate-logs`, lệnh tái hiện `scripts/verify_p00.py`. Có ca âm cho package thiếu thành phần, business path sai, duplicate/unknown IDs, JSON duplicate keys, NaN, bool thay number, log lệch submission và coverage thiếu.

Kết quả có thể tái hiện và các acceptance còn chưa xác minh nằm ở `reports/p00_results.md`. Không dùng kiểm tra public format thành vòng tuning/chấm nội dung public test.
