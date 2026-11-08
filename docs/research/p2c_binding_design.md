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

## Bổ sung sau review: giới hạn mở rộng rule — 08/11/2026

Nguồn: phản biện PR#6 tại664e5d4 và yêu cầu người dùng bổ sung hai tiêu chí
vào note thiết kế. Đây là giới hạn cho bước P2c tiếp theo, chưa là khả năng
đã triển khai hoặc kết quả chẩn đoán mới; giữ nguyên G2/split/scorer.

Chẩn đoán trên18business dev, lập bảng local theo từng business và từng
metric `order_count`/`revenue_total`. Mỗi blocker ghi nguồn/locator/hash,
vai trò nguồn cần giải thích, mẫu cấu trúc, số business/cụm có cùng mẫu và
bằng chứng còn thiếu. Một business có thể có nhiều blocker; không ép mọi
nguyên nhân vào một loại duy nhất. Chỉ đưa số liệu tổng hợp ra báo cáo repo,
không commit membership hoặc dữ liệu/packet BTC.

| Loại | Blocker | Cách xử lý |
|---|---|---|
| (a) | Cấu trúc phổ biến mà core đã hỗ trợ, như header–detail hoặc events | Nối binder với core, kiểm quan hệ khóa/cardinality/orphan và nghĩa nghiệp vụ trước khi công bố capability |
| (b) | Cấu trúc mới nhưng lặp lại | Chỉ bổ sung khả năng rule khi cùng mẫu xuất hiện ở ít nhất2business; ưu tiên thuộc ít nhất2cụm |
| (c) | Quyết định ngữ nghĩa chưa đủ căn cứ, như vai trò nguồn, nghĩa tiền hoặc nhãn trạng thái | Chuyển sang LLM đề xuất có evidence; CPU kiểm phần kiểm được, chưa đủ căn cứ thì chờ duyệt hoặc abstain |

Mọi khả năng binder mới, kể cả nối core cho(a), cần bằng chứng mẫu lặp ở
ít nhất2business trước khi chọn làm rule chung; số cụm phải báo riêng, không
coi2business cùng mẫu là bằng chứng tổng quát hóa. Mẫu chỉ có ở1business
để LLM đề xuất/CPU kiểm hoặc abstain, không viết nhánh riêng theo business.
Fixture synthetic kiểm được hành vi/phản ví dụ, không thay số business thật.

Xét mức liên quan của nguồn theo từng metric. `order_count` không bị chặn
chỉ vì chưa giải được tiền/quy đổi; vẫn phải đủ bằng chứng ngày/trạng thái/
nguồn ảnh hưởng tới đếm đơn. Không loại nguồn chỉ vì thiếu ngày hoặc không
thấy mã đơn trùng trực tiếp. LLM trích đúng README chỉ chứng minh đoạn dẫn
tồn tại; chưa chứng minh mapping đúng nghĩa hoặc đủ nguồn.

Điểm dừng bước rule: chẩn đoán trước, chỉ làm(a)/(b) đủ điều kiện lặp;
(c) chuyển thẳng sang nhánh đề xuất LLM, không kéo dài từ điển để né phần
ngữ nghĩa. Sau lượt nối header–detail/events đủ điều kiện và đo lại, nếu
vẫn chưa có business qua kiểm cho metric đang xét ở cụm thứ hai thì dừng
mở rộng rule trong lượt này, ghi blocker còn lại và chuyển sang LLM. Không
nới guard để tăng số qua kiểm. Chưa ấn định số giờ; không coi ước lượng
"nửa ngày" là thời gian đã đo hoặc cam kết hoàn tất.

LLM phân tích business theo thiết kế hai tầng tại `p2c_cpu_design.md`, cache
theo content/code/model/rulebook hash; đổi evidence phải vô hiệu cache.
Điểm dừng rule không tự cấp quyền chạy job: vẫn kiểm account/budget trước
Modal và giữ scope dev đã được cấp. Mỗi hàm vẫn cần bằng chứng đúng trên
ít nhất2cụm trước nghiệm thu P2. Audit binding không thêm cổng6business hay
15câu/cụm trước model. Acceptance PA nội bộ từng hàm theo domain_scope vẫn
cần>=15answered/cụm và precision>=90% ở>=2cụm; không bỏ hoặc gộp hai cổng.
Calibration tiếp tục hoãn. Chưa chạy chẩn đoán mới, model, throughput hay PA
trong lần cập nhật note này.

## Tài nguyên và bước sau

### Phép thử structural round — 08/11/2026

Reconnaissance bằng scoped verified reader ởmain664e5d4:18dev/212unit,
71mẫu header chính xác,18mẫu lặp giữa business; header thiếu evidence không
được tính là mẫu header đã hiểu. Chi tiết chỉ local tại
`runs/p2c-structural-20261108/`; không mở gold.

Giả thuyết: binder có thể tăng số qua kiểm bằng nối core header–detail và
event số lượng trả có định nghĩa rõ, cùng nhận diện bảng quy đổi theo định
nghĩa cột thay vì chỉ tên cột. Bảng quy đổi4cột lặp5business/1cụm; header–detail
và số lượng trả lặp>=2business. Chỉ nhận nghĩa đóng đã xuất hiện lặp; bảng
không đủ định nghĩa, nhãn lạ, net chưa rõ hoặc layout singleton vẫn unresolved.
Phương án bỏ nguồn theo thiếu ngày/khóa bị loại vì không chứng minh độc lập
metric; LLM vẫn dành cho phần nghĩa còn thiếu sau lượt bounded này.

Phép thử: synthetic đếm2đơn/3dòng, một đơn returned qua quantity>0; duplicate
header, orphan detail và orphan event kể cả quantity0 phải fail. Giá trị tiền
không parse không chặn count, nhãn trạng thái lạ phải chặn cả hai metric.
Mapping event chỉ đổi quantity>0 thành returned theo policy core hiện hành;
không triển khai trừ doanh thu một phần hoặc dùng ngày trả thay ngày đặt.
Audit18dev mới đo theo metric/cụm, giữ kết quả fail cũ, không gọi machine-check
là binding được duyệt độc lập hoặc PA. Sau vòng này áp dụng điểm dừng đã chốt.

Kết quả vòng đầu vẫn1/18/1cụm; dừng thêm khả năng rule. Probe LLM kế tiếp
chỉ tối đa16case metadata/status dev, chọn theo hash và cụm, không theo gold.
Nguồn: schema/README đã xác minh, nhãn trạng thái lấy từ tối đa128dòng đầu
của unit được chọn; đây là mẫu để đề xuất, không phải inventory đủ hoặc phép
đo độ đúng. Tách case vai trò/cột nguồn và case trạng thái để giới hạn output256
token/context4096. Hash cache gắn nội dung/code/model/rulebook; tối đa1job,
không retry hoặc tự áp mapping. CPU kiểm JSON, cột có thật và trích dẫn đúng
substring nguồn; mọi đề xuất vẫn pending semantic review. Thiếu căn cứ trả
unknown. Không thay capability/binding dựa riêng vào quote hợp lệ.

So với phân tích tất cả212unit ngay, probe nhỏ kiểm được đường vận chuyển/
cache/citation với chi phí hữu hạn trước khi mở rộng. Phép thử phân biệt:
quote bịa/cột ngoài source/truncated phải bị từ chối, nguồn thực phải được
rebuild từ scoped reader trước upload; output thật phải có model revision,
snapshot/offline/read-only/memory evidence. Người dùng xác nhận credit>=30USD
ngày08/11; vẫn xác minh account/dự toán trước job, billing cap không phải hard.

Lượt cloud đầu fail trước inference do helper diagnostic kéo pydantic vào
Python hệ thống. Phép thử Python-S đã tái hiện, sau tách sanitizer stdlib
thì pass; cả staging/GPU đóng gói helper mới, API model_probe giữ tương thích.
Cho một lượt kiểm chứng revision đã sửa sau CPU/review/preflight, SDK vẫn
retries0; giữ artifact lỗi, dự toán dự phòng gộp20USD dưới ceiling30USD.
Không tự lặp lại revision lỗi hoặc đổi cấu hình model để che lỗi môi trường.

Audit tuần tự, streaming, từng business trong subprocess có timeout và đo peak
RSS/elapsed; không trả ledger qua IPC. Mỗi child chỉ2CPU/DuckDB256MB; giới hạn
ledger rows/estimated bytes explicit, vượt thì ghi resource_guard, không cắt
rồi báo pass. Chỉ source artifacts tối thiểu local, không publish BTC.
Bindings tự động chưa đủ để trả lời câu thật đến khi được duyệt theo scope.
Sau binding mới làm short prompt/probe throughput đã chốt; không chạy model
toàn1895dev ở increment này. Billing vẫn cần actual dashboard khi công cụ hoạt động.

## Cache cũ và provenance

Lượt audit đầu bị `stale_ingest_identity` ở cả18business, trước khi binder
đọc dòng dữ liệu. Code ingest đã đổi sau generation A-T2; thử toàn bộ tổ hợp
LF/CRLF của5file ingest hiện hành không khớp hash cũ. Không bỏ kiểm tra code
hash hoặc sửa manifest để dùng lại cache. Dựng generation/profile mới chỉ cho
18business dev đã authorize, giữ options ingest/profile cũ và giữ nguyên
source/cache cũ. Báo lỗi provenance này riêng, không tính thành18binding sai.
Đối chiếu Git chỉ để chẩn đoán: hash cũ khớp chính xác5file ingest LF tại
`790b1af`; các commit sau đổi docstring, vị trí import và formatting. Không
checkout/chạy mã cũ hoặc khôi phục timeline lịch sử.

Review lượt hai bổ sung guard: tọa độ header phải khớp và data_start là hàng
không rỗng đầu tiên sau header; annotation bỏ qua hàng không rỗng chưa được
v0 chấp nhận. Chỉ dùng vocabulary A-T2 thực `auto_rule`, `source_schema`,
`explicit_annotation`. README có định nghĩa mâu thuẫn/chưa hiểu thì veto
mapping của header quen thuộc; không coi định nghĩa đó là thiếu để fallback.
