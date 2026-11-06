# Core CPU P2c

`datamate.domain_lib` có resolver kỳ, ledger từ mapping rõ ràng và hai hàm
`revenue_total`/`order_count`. Đây là core đã kiểm synthetic; chưa là backend
predict hoặc business adapter được nghiệm thu trên dev. Không đọc gold,
không tải model, không chạy SQL từ model.

Consumer chịu trách nhiệm kiểm file/hash, chọn đúng row role, cột/nghĩa/đơn
vị và cung cấp iterator đầy đủ. `BoundSource.sha256` ghi provenance, không tự
hash lại file. Chỉ cột net line amount **sau** chiết khấu dòng được bind vào
amount; VAT/ship/voucher toàn đơn không thuộc amount. Chưa chứng minh nghĩa
hoặc grain thì không tạo capability. Reader và audit binding CPU research
đã có; duyệt mapping business thật và nối vào predict vẫn là bước riêng.

Ví dụ sau chỉ là fixture synthetic, hash không phải bằng chứng dữ liệu thật:

```python
from datetime import date
from datamate.domain_lib.orders import Binding, BoundSource, RawRow, adapt_sources
from datamate.domain_lib.periods import resolve_period
from datamate.domain_lib.metrics import revenue_total, order_count

binding = Binding(
    role="lines",
    order_id="order",
    placed_at="placed",
    status="state",
    amount="net_line",
    status_values={"done": "completed"},
)
rows = [
    RawRow(
        1,
        {
            "order": "synthetic_A",
            "placed": "2026-11-01",
            "state": "done",
            "net_line": "100",
        },
    )
]
ledger = adapt_sources([BoundSource("synthetic_export", "a" * 64, binding, rows)])
period = resolve_period("tháng này", date(2026, 11, 7))
assert revenue_total(ledger, period) == 100
assert order_count(ledger, period) == 1
```

`RawRow.cells` phải chứa **toàn bộ cells dữ liệu gốc**, chưa chiếu riêng các
cột dùng tính tiền; nếu bỏ cột thì không còn chứng minh “trùng mọi ô”. Không
đưa tọa độ vật lý vào cells, tọa độ nằm ở `RawRow.row`. Các source unit khác
nhau có thể chứa cùng export; dedupe vẫn theo order ID + toàn cells, giữ refs.

Headers được gom theo order ID, không join nhân dòng. Header không được che
status/entity khác trên line. `events` chỉ nhận huỷ/trả đã ánh xạ rõ, không
infer trả hàng từ số âm; event được xét trước lọc kỳ dù ngày sau as_of.
Blank carry là boolean explicit, chỉ nhóm liên tiếp trong cùng source.

`EntityBinding(code, label, scope)` có scope order/line. `Filter` nhận code
hoặc exact normalized alias duy nhất; giữ dấu, không fuzzy. Thông tin entity
thiếu là unknown; chỉ khi source chứng minh blank nghĩa không có thực thể
mới đặt `blank_is_absent=True`. Mọi dimension/mention cần được verifier kiểm,
không bỏ filter không hiểu. Core không kiểm độ đầy đủ của điều kiện trong
câu hỏi; short-intent parser/verifier còn là bước riêng.

`DomainAbstain.code` cần được caller chuyển thành abstain qua formatter hiện
có. Không bắt lỗi rồi thay bằng0. Thiếu tiền không ngăn count nếu grain/date/
status còn đủ; revenue abstain khi tiền của line phù hợp không hợp lệ.
Ngoài extent bảo thủ abstain; zero chỉ trong extent đã có evidence.

Date source chỉ ISO calendar YYYY-MM-DD, D/M/YYYY hoặc D thg M YYYY theo
binding; số plain, vi hoặc en explicit, không đoán separator. Resolver cụm kỳ full-match;
so sánh tháng này dùng L32. Tết/âm lịch và comparison chưa rõ luật abstain.
Giới hạn rows/estimated bytes là application guard, không là peak RAM đã đo.

[Thiết kế](research/p2c_cpu_design.md), [scope](research/p2c_domain_scope.md),
[bằng chứng](../reports/p2c_cpu_results.md). Full-dev precision/PA/G2 vẫn pending.

## Audit binding CPU research

`scripts/p2_binding_audit.py audit --profile-index <profile.json> --output <new-directory>`
chỉ authorize context dev từ split đã khóa. Mỗi business chạy subprocess
riêng,2threads/DuckDB256MiB, timeout90giây; không đọc gold hay gọi model.
Reader đối chiếu source inventory, code/runtime, cache/catalog, profile/schema
và header evidence trước/sau đọc. Cache lệch identity phải dựng lại bằng
ingest/profile hiện hành; không sửa hash trong manifest để vượt guard.

Rule binder chỉ nhận mapping cột có nghĩa rõ; mọi unit phải được bind hoặc
thuộc signature bảng quy đổi đóng. Nguồn chưa giải thích, trạng thái lạ hay
ngày mơ hồ làm business chưa qua kiểm. Gate đếm đơn độc lập với gate tiền.
Số học≥95% là screen phụ; không thay định nghĩa net, không chọn scale tiền
nếu thiếu dòng phân biệt hoặc nhiều grammar vẫn cho giá trị khác nhau.

Artifact `binding.json`, `businesses-local.json` và `review-packet-local.md`
chứa dữ liệu nguồn nên giữ local trong runs. `machine_checked` chưa là oracle
được duyệt, precision hay G2; chưa tự cấp quyền trả lời trong predict.
[Thiết kế và giới hạn](research/p2c_binding_design.md).
