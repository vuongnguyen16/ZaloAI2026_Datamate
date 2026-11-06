# P2c: reader và binding CPU trước LLM

Ngày07/11/2026, base98c1c1e. Thuộc P2 đang active, không đổi G2/split/scorer.
Nguồn: scope/core P2c, timeline hiện hành, README/header/profile dev và review
người dùng. Chưa đọc gold mới, không model/cloud/billing action.

## Quyết định

Rule-first dựa trên nghĩa cột được README mô tả, header A-T2 và parse toàn
dữ liệu được chọn. Không dùng question/business ID làm rule; không tune theo
gold. Reader kiểm source/cache/profile/schema hashes và catalog, read-only,
2threads/DuckDB256MB; không nạp lại raw hoặc bỏ qua rows để làm pass.

Phân biệt3mức: candidate; qua kiểm CPU theo từng metric; được duyệt binding
độc lập. Tác giả tự đối chiếu chỉ là author_checked, không oracle độc lập.
Packet duyệt chứa locator/hash/column/status/format/discrepancy samples chỉ
local. Code/synthetic và aggregate được review hai lượt theo yêu cầu người
dùng; không gửi kit/gold/packet BTC cho subagent. Human spot-check còn pending.

## Reader và phạm vi đầu

Đọc generation A-T1/A-T2 có hash và catalog đúng; chỉ decode business dev đã
authorize ở CLI research. API reader generic để inference sau này dùng được,
không hardcode split/business. Đọc đầy đủ mọi cột data positional cho dedupe;
giữ __row làm tọa độ riêng, raw không đổi. Iterator fetch từng batch.

Chỉ bỏ prefix đã có header evidence, hàng rỗng, exact repeated header và
printed-total có marker rõ + không date/status/product. Ghi mọi loại row/count
bị loại; dòng không giải nghĩa làm fail, không silently skip. Printed total
chỉ đối chiếu khi có cùng metric/scope; không coi tổng phải thu/VAT là revenue.

Binder v0 ưu tiên bảng dòng hàng kết hợp đủorder/date/status/net có định nghĩa
README “thành tiền sau giảm”. Có thể nhận nhiều sheet/part cùng layout. Header
thuần có thể hỗ trợcount riêng; revenue nhiều bảng/nghĩa chưa rõ được báo pending.
Nguồn trả hàng không bind được làm fail, không bỏ qua vì header đã có status.
Status map từ tập literal có nghĩa rõ; nhãn lạ cần duyệt, không guess bằng prefix.

Format ngày/số explicit: chọn trong grammar đóng, parse coverage100% trên giá
trị liên quan; blank chỉ được carry theo nhóm đã có ID. Bổ sung grouped-comma
money và ngày “D thg M YYYY” nếu được test. Nếu nhiều grammar cho giá trị tiền
khác nhau, chỉ chọn khi evidence số học phân biệt được; không dùng độ lớn tiền
hay gold để chọn locale. Ambiguous thì revenue chưa qua, count có thể vẫn qua.

## Kiểm CPU, không biến95% thành bằng chứng ngữ nghĩa

- Grain/date/status: mọi dòng cần giải thích, mọi label nonblank đã map, ledger
  không conflict/orphan; mọi source liên quan được bao phủ. Count không cần tiền.
- Revenue: net semantic từ README; amount parse đầy đủ; số học qty*price-discount
  là check bổ sung.95% là screen cảnh báo đã ghi trước đo, không cho phép chọn
  cột pre-discount dù khớp100% trên các dòng discount0. Cần báo số informative
  rows và các grammar/công thức còn tương đương, không dùng CI/PA để chọn mapping.
- README ngày cuối so với order extent là diagnostic; mismatch không tự sửa
  ngày hoặc suy ledger sai, vì nguồn có thể ghi ngày snapshot/sheet khác.
- Printed total có cùng scope mới so, khác định nghĩa báo not_comparable.

Báo18business và4cụm với reason; “qua kiểm CPU” không là precision/G2. Dùng
taxonomy đã pin để báo upper-bound ứng viên/cụm; không hứa>=15answered khi chưa
parser/model và evaluator. Không dùng calibration/holdout để bù.

## Tài nguyên và bước sau

Audit tuần tự, streaming, từng business trong subprocess có timeout và đo peak
RSS/elapsed; không trả ledger qua IPC. Mỗi child chỉ2CPU/DuckDB256MB; giới hạn
ledger rows/estimated bytes explicit, vượt thì ghi resource_guard, không cắt
rồi báo pass. Chỉ source artifacts tối thiểu local, không publish BTC.
Bindings tự động chưa đủ để trả lời câu thật đến khi được duyệt theo scope.
Sau binding mới làm short prompt/probe throughput đã chốt; không chạy model
toàn1895dev ở increment này. Billing vẫn cần actual dashboard khi công cụ hoạt động.
