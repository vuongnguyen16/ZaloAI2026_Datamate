# Chuyển nguồn kế hoạch sang Timeline A–G

Ngày 04/11/2026, giờ Việt Nam. Người dùng xác nhận đã xóa các plan cũ và muốn
bắt đầu lại theo `Research/Timeline DataMate theo nhóm việc A–G.docx`.
Đây là quyết định thay thế roadmap; không khôi phục plan cũ từ Git.

## Nguồn và giả thuyết

Đã đọc toàn bộ đoạn văn, bảng và kiểm tra phần ghi chú OOXML của timeline.
SHA-256 DOCX: `e74b1292119f01ca3eae7d20d709921219efc30e655e01909685c50d5363eb51`.
Timeline nhóm A xử lý dữ liệu; B tiếng Việt; C nghiệp vụ; D suy luận;
E đánh giá; F huấn luyện có điều kiện; G hạ tầng/vận hành.
Các mốc ngày trong DOCX là dự kiến, không thay thế thể lệ hoặc xác nhận lịch của BTC.

Giả thuyết: giữ foundation đã kiểm thử và thay toàn bộ chỉ dẫn tiến độ cũ sẽ
cho phép bắt đầu A–G mà không phải dựng lại môi trường/contract, đồng thời tránh
nhầm artifact kế thừa với module mới hoàn thành.

## Lựa chọn và quyết định

| Phương án | Hệ quả | Quyết định |
|---|---|---|
| Xóa toàn bộ code/tests/config | Mất nền contract, bảo vệ raw và bằng chứng; phải làm lại không cần thiết | Loại |
| Giữ cả các note/report/tracker cũ | Hai nguồn định hướng; harness vẫn hồi sinh plan đã bị bỏ | Loại |
| Giữ foundation, gộp bằng chứng cần thiết, bỏ note tiến độ và thay tracker theo A–G | Ít code mới, giữ kiểm thử hành vi, một nguồn kế hoạch | Chọn |

## Đối chiếu các thành phần giữ lại

| Thành phần | Phục vụ timeline | Giới hạn cần ghi đúng |
|---|---|---|
| uv/lock, doctor, src-layout, CPU gate, CI, repo skill | G, hạ tầng phát triển | CI remote và discovery ở phiên mới chưa đo |
| Question/output contracts, validator, predict.sh, fake runner, logs/hash | E/G | Chỉ cấu trúc/wiring, chưa scorer hoặc baseline model |
| Inventory cơ học và regression | A/T1 | Chưa khảo sát số dòng, cột hoặc nội dung README; chưa loader đa định dạng |
| Contract/provenance/kit hashes | E/G và chính sách dữ liệu | Quy tắc quan sát 01/11; không tự coi deadline lịch sử là lịch mới |
| Modal config/app/runbook và kết quả smoke lịch sử | D/G | Chưa real model/GPU; xác minh lại tài khoản/budget trước job |
| Dockerfile/.dockerignore bản nháp | G, đóng gói cuối pipeline | Giữ nguyên; không build/test/chỉnh trong cleanup |

## Phạm vi thay đổi

- Backup có hash 32 file bị ảnh hưởng tại
  `runs/timeline-reset-backup-20261104-233607/`, local/ignored; không backup dữ liệu
  BTC bằng cách đọc lại nội dung. Raw, kit manifest và DOCX timeline giữ nguyên.
- Xóa note research và report tiến độ cũ theo S00/P00/P01/H00 sau khi chuyển phần
  nền có giá trị sang `docs/foundation.md`; giữ machine-readable contract evidence.
- Đổi tên inventory/verify/tests/provenance sang tên theo chức năng, sửa callers.
- Viết lại README/AGENTS/state/backlog/harness/skill theo A–G. Module chưa làm là
  todo, phần kế thừa chỉ công nhận đúng phạm vi; không tạo hàng loạt module rỗng.
- Context trả path/hash của timeline hiện tại. Timeline thiếu phải báo thiếu,
  không đọc Git fallback hoặc dùng plan cũ trên đĩa.

## Kiểm chứng và điều kiện giữ

Giữ khi CPU gate chuẩn pass, các regression của foundation vẫn còn nguyên hành vi,
context tìm được A-T1 và timeline đúng hash, ID task cũ bị từ chối, không còn chỉ
dẫn đang có hiệu lực buộc theo roadmap cũ. Test đổi expectation của plan fallback là thay
contract có lý do từ yêu cầu mới; không xóa regression fail-fast/hash/dữ liệu.
Thêm ca âm: plan cũ tồn tại nhưng timeline mới thiếu vẫn không được fallback.
Kết quả cuối ghi ở `reports/timeline_reset_results.md` và state/backlog.
Không chạy cloud, model, Docker, scorer, upload hoặc push trong increment này.
