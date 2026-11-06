# P2c CPU: ledger, resolver và hai chỉ số

Ngày07/11/2026, từ main6ac467e; P2 vẫn active, chưa qua G2.
[Thiết kế](../docs/research/p2c_cpu_design.md),
[plan](../docs/research/p2c_cpu_plan.md),
[scope](../docs/research/p2c_domain_scope.md).

## Đã triển khai và giới hạn

- `domain_lib/orders.py`: raw rows theo binding explicit→ledger mã đơn,
  source/hash/binding fingerprint và lineage. Dedupe cùng đơn bằng toàn bộ
  cells gốc, giữ tọa độ cả dòng trùng; khác ID vẫn là đơn khác. Header lặp
  không nhân tiền; sự kiện trả/huỷ, kể cả sau ngày neo, loại toàn bộ đơn.
- `periods.py`: resolver strict full-match, ngày/tháng/quý/năm, relative/YTD,
  tuần Mon và previous-month comparison L32. Relative current bucket không
  lấy record tương lai. Tết/âm lịch chưa có adapter calendar: abstain rõ.
- `metrics.py`: revenue từ net line amount, Decimal và round VND ở cuối;
  count mã unique, độc lập thiếu tiền. Filter exact code/alias duy nhất,
  có scope order/line; không hiểu/mơ hồ/thiếu thông tin ảnh hưởng thì abstain.
  Kỳ ngoài extent bảo thủ không là0; gap trong extent có thể0.

Caller phải cung cấp binding đã kiểm, iterator đầy đủ và hash nguồn đúng;
core không tự chứng minh hash khớp file hoặc cột đó đúng nghĩa net revenue.
Chưa có reader/binding business thật được nghiệm thu, chưa nối vào predict,
chưa tự suy schema/SQL, chưa inference/PA/per-cluster acceptance. Synthetic
pass không thay precision>=90% trên>=2cụm, mỗi cụm>=15câu đã trả lời.

## Ba minor P2b đã sửa

Giới hạn từng filter string256ký tự cả schema/parser; checkpoint sau engine
init và warmup có phase/memory metrics; snapshot failure giữ stderr được
sanitize và cắt4096ký tự, commit evidence trước khi raise. Image chỉ bổ sung
helper source, không data. Regression3ca RED rồi GREEN; bộ liên quan15pass.
Chưa chạy lại model sau thay đổi schema/worker, không mượn P2b cũ để claim
runtime mới đã kiểm thật.

## Bằng chứng CPU

28test resolver và17test ledger/metrics, cộng3regression diagnostics:
48test liên quan pass. Fixtures hoàn toàn synthetic, không gold hay business-ID
special case. Test tiền lớn hơn2^53, định dạng số explicit, status4loại,
trả một phần ở tương lai, không mutation, header1–n, lineage trùng/event,
lọc order+line/alias trùng/thiếu entity, giới hạn rows/bytes, ngoài dữ liệu,
VND round sau cộng, năm nhuận và ngày đầu tuần/tháng/năm.
Hai regression bổ sung đã RED→GREEN: thiếu event lineage và thiếu cột tiền
làm mất khả năng đếm đơn. Full gate/review cuối được ghi sau kiểm chứng.

## Trước khi chạy toàn dev qua model

[Bổ sung báo cáo P2b](p2b_context_probe_results.md#bổ-sung-sau-review0711)
nêu rõ throughput/độ dài chỉ là mẫu, KV chưa là nguyên nhân duy nhất.
Thiết kế chọn business analysis có chunk/cache+CPU verification, intent ngắn
<=1024token và enum/index output<=64token; chưa có model adapter mới hoặc
kết quả tốc độ mới. Mốc3000câu/2replica trong<=5400s gồm load/warmup/business
analysis; floor0,28request/s/GPU chưa đủ bảo đảm tổng thời gian. TP2 phải đo
aggregate, không giả định nhân đôi. CUDA graph/prefix cache/seq8–16 phải đo
VRAM/latency thật trước full1895dev. Batch schedule ổn định vẫn cần test lặp.

Đã thử đọc billing bằng Computer Use, nhưng node runtime và CUA đều lỗi khởi
tạo trên Windows; chưa truy cập dashboard, chưa có actual bill. Không biến
ước tính GPU10phút thành chi phí thực toàn job, không ghi0USD hoặc chạy thêm
GPU để hiệu chỉnh. Fresh account/budget và runtime evidence vẫn là điều kiện
của probe tiếp theo.
