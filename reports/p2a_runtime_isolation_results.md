# P2a follow-up: mục output ngoài runner và timeout từng câu

Basee17a14b, branchwork/p2a-runtime-isolation,06/11/2026.
[Thiết kế](../docs/research/p2a_runtime_isolation.md),
[plan](../docs/research/p2a_runtime_isolation_plan.md).

## Đã sửa

- Root admission chỉ kiểm logs/final là đường dẫn owned. lost+found/user file
  hay mục khác chỉ lấy tên, không stat/resolve/open/xóa nội dung. Tên được ghi
  ở diagnostics của normal run và failsafe. Root/owned-path/link/writer guards
  và private checkpoint admission không được nới.
- Loại consecutive-errors cutoff. Timeout/query error không tắt backend theo
  số lần; startup_error/worker_exited/invalid_worker_result vẫn ngừng backend.
  Global deadline/output budget giữ nguyên. Không thêm circuit breaker mới.

4regression fail trước sửa;9case pass sau sửa, gồm unmanaged no-read/no-stat,
failsafe diagnostics,3timeout/error rồi câu sau trả lời, proven backend failure
và type conflict ở logs/final. Bộ liên quan58passed/1skipped trong40.24s,
gồm writer cạnh tranh/identity khác, kill/resume, exclusive publication và worker.
Skip là quyền symlink Windows, Linux CI phải chạy thật.
Review độc lập/full CPU/CI đang chốt; không dùng gate cũ để claim source mới.

Hai assertions cũ yêu cầu từ chối user.txt được cập nhật theo yêu cầu mới;
không bỏ test lock/final hoặc private RunStore guard để pass.

## Bước sau, chưa thực hiện trong increment runtime

Ba khảo sát CPU dev làm tuần tự: tách ô405 theo lọc/kỳ/grain và ambiguity;
sample khoảng40gold dev (10/cụm, phân tầng kỳ) bằng scoped reader; trích rulebook
kèm locator cho date/status/count/returns/discount/VAT/shipping/comparison.
Gold preview chỉ tìm dấu hiệu, không suy quy tắc rounding từ mẫu nhỏ.

P2c: revenue_total và order_count chính; revenue_change_pct tùy chọn sau total ổn.
Internal per-function acceptance do người dùng chốt: answered=correct+wrong,
precision>=90% trên>=2cụm dev đã khóa, mỗi cụm answered>=15; thiếu thì chưa đủ mẫu.
Với15answered cần>=14correct. Không là significance claim, không thay G2 toàn dev.
Note phạm vi cuối viết sau khảo sát, trước PA; prompt/cache spec rồi mới probe P2b.
Chưa domain_lib, gold preview, model/job mới, PA, hoặc thay split/access/G5.
