# P2c: loại nguồn đã được duyệt, có phạm vi — 08/11/2026

Nguồn: người dùng duyệt6catalog/payment sources trong packet C3 có SHA
`ad4d9eac132aa45e9a996bf9ebff8dc95318c5a133971ca4da513ddc944b34fa`;
`p2c_count_feasibility_review.md`, verified reader, audit/source plan và
acceptance domain_scope. Quyền chỉ default-unfiltered order_count và
revenue_total;6unknown và17nguồn khác giữ nguyên. P2 active duy nhất.

## Thiết kế được triển khai từ phạm vi đã duyệt

Một artifact local mới: version/kind/dev/scope/đúng cặp metrics/rulebook SHA,
receipt reviewer/time/draft packet SHA; mỗi business có proof đã xác minh,
mỗi unit có ID/file/name/full-unit SHA/raw-file SHA/README SHA/role và decision.
Chỉ master/payments, chỉ explicit approved_exclude. Không theo basename/ID
trong code; ID chỉ là khóa tới nguồn đã review. Packet/draft gốc không sửa.

Loader đòi SHA caller truyền, bounded strict JSON/schema, receipt rõ và scope
dev được authorize; từ chối pending/hash/scope/metric/duplicate/role sai.
Matcher kiểm proof/unit/raw/README với VerifiedBusiness hiện hành. Chỉ loại
plan unresolved; không được bỏ order/header/detail/return/conversion đã nhận
diện. Unknown unit hoặc stale identity fail-closed. Call scope/filter khác
default-unfiltered bị từ chối. Human receipt là trust local, không chữ ký số.

Audit giữ unit_coverage đầy đủ, đánh dấu excluded_by_review + hash/role/scope;
không gộp vào rule recurrence hoặc xóa raw hypotheses. Blocker của các unit
đã loại được tách khỏi effective diagnosis;17nguồn khác không thay đổi.
Ledger và count/revenue data gates, row/memory guards vẫn chạy trên toàn bộ
nguồn còn liên quan. Physical row_scan không gọi complete khi nguồn excluded
chưa đọc; thêm required_row_scan_complete riêng cho các nguồn ledger cần.
Không cấp filter capability hoặc full-business independent approval từ receipt.

CLI thêm cặp --source-exclusions / --exclusions-sha256, audit/worker-only;
kiểm receipt trước đọc dữ liệu/output, forward cùng path/hash tới từng worker.
Giữ audit không flag như cũ. Receipt mới chỉ6nguồn đã được duyệt, không tự
phê duyệt các proposal khác hoặc đổi lexicon approved.

## Phương án và phép kiểm

Loại theo tên file bị loại vì overfit và không có identity/scope. Bỏ mọi
nguồn phụ hoặc chạy ledger bỏ qua veto bị loại vì có thể mất sự kiện trả.
Chọn explicit receipt để người dùng có thể review/revoke và CPU kiểm stale.

Synthetic RED→GREEN: pending/stale/nondev/filtered/subset-metric/duplicate;
đúng receipt mở nguồn phụ nhưng không bypass unknown status, raw identity,
nguồn order/return, nguồn chưa duyệt khác hoặc resource guard. CLI không cặp
flag/diagnose/pending phải dừng trước auditor/output. Không đọc real kit trong
test hoặc review agent. Audit thật18dev sau final code, chỉ CPU/no-gold/model.
So với baseline đã áp lexicon: mỗi metric business/cụm/pass/regression và
blocker còn lại; không suy PA/15answered/G2 từ binding được mở.
