# Phạm vi domain_lib v0 trước đo PA

Ngày 07/11/2026, sau runtime PR #3 (`2f1dbb2`). Đây là phạm vi thiết kế
thuộc P2, chưa có domain_lib hoặc kết quả PA. G2 toàn dev giữ nguyên.

## Căn cứ và khảo sát CPU

Timeline SHA `499fe26b696d5d8eb5d71117c927e57438cbfa96064934da5e2fccc918451d28`;
split SHA `b28dd4fa7fb34b7a0ed356c7ec11f32f84911bcdf71fcd128c2c5082b208fa18`;
taxonomy SHA `e1cd00a41c741203c3d5bf1350a8774fa840a0fe7176090277c49cc74da262f1`.
Nguồn định nghĩa là `data/train/rulebook.md`, SHA
`740267bccba29df70f745bc39968bbec5b3e62dada2c858c45314f3ec723d113`.
Locator dưới đây là dòng của đúng phiên bản đó, không phải kết luận từ gold.

Khảo sát local `runs/p2c-cpu-surveys-20261107/`:

- Ô revenue/aggregation/number/absolute có405 ID unique. Dấu hiệu lọc rõ146,
  mơ hồ105, chưa thấy dấu hiệu154. Chiều lọc chồng nhau: sản phẩm58,
  trạng thái/khác57, khách24, nhân viên8, kênh4. Chưa thấy dấu hiệu không
  chứng minh không có lọc: tên riêng, viết tắt hoặc lỗi gõ vẫn có thể bị sót.
- Độ hạt heuristic: tháng372, quý14, ngày14, khoảng ngày4, năm1. Bộ nhận diện
  sau sửa không thấy yêu cầu nhiều kỳ/chia nhóm trong ô này; chưa human-review
  toàn bộ, không xem đây là chứng minh mọi câu chỉ có một kỳ.
- Có73 câu mang dấu hiệu trung bình. Nhãn aggregation chồng với average;
  vì vậy405 không phải405 câu tổng doanh thu, cũng không phải độ phủ dự kiến.
- Chọn cố định40 câu trước khi đọc đáp án:10/cụm, luân phiên strata chỉ số và
  dạng kỳ, thứ tự hash `p2c-sample-v1`. Đọc đúng40 record gold dev qua authorize
  rồi routing tập con;2960 record còn lại chỉ routing envelope. Không decode
  gold calibration/holdout. Danh sách chọn/hash/audit giữ local.
- Mẫu gồm20 revenue-number và20 revenue-comparison-percent.20 number đều
  nguyên, độ lớn khoảng10^5–10^9; có1 câu mang dấu hiệu trung bình, nên không
  gọi toàn bộ20 là tổng doanh thu.20 percent đều có phần lẻ, tối đa2 chữ số;
  có7 số âm. Đây là dấu hiệu nhất quán với nguồn, không chứng minh tie rounding
  hoặc quy tắc mới. Một cụm không có ứng viên percent theo taxonomy; mẫu tại
  cụm đó là10 number. Không lấy calibration/holdout để bù strata.

Synthetic local5 test pass; đã có regression RED→GREEN phân biệt “mỗi đơn”
với nhiều kỳ. Phân loại câu hỏi chỉ dùng text; gold chỉ dùng khảo sát dạng số.
Không có model, PA, tuning prompt hoặc kiểm precision ở khảo sát này.

## Hai hàm chính và thứ tự

1. `revenue_total(period, filters)` trả number. Bắt đầu kỳ tuyệt đối rõ,
   rồi ngày tương đối; resolver dùng `as_of_date`, không LLM làm phép tính.
2. `order_count(period, filters)` trả number. Dùng chung tập đơn hợp lệ,
   nhưng đếm mã đơn duy nhất, không đếm dòng hàng/phiếu thu/đợt giao.
3. `revenue_change_pct(period, comparison, filters)` là tùy chọn, chỉ sau
   `revenue_total` ổn định. Không xem việc tái dùng hàm là bằng chứng độ đúng.

Chỉ nhận một kết quả scalar thuộc đúng họ. Trung bình, tỷ trọng, xếp hạng,
quantity/quy đổi, giá, công nợ và các họ khác abstain ở v0. Trung bình được
hoãn vì phạm vi và grain, không vì rulebook thiếu quy tắc làm tròn.
SQL fallback/single_sql/tracing đầy đủ vẫn ở P4–P5.

## Định nghĩa phải được adapter dữ liệu chứng minh

| Điểm | Quy tắc và locator rulebook |
|---|---|
| Ngày ghi nhận | Ngày đặt đơn, không ngày giao/thu tiền: L12; số đơn dùng cùng tập đơn L14 |
| Trạng thái | Hoàn thành và đang giao được tính; huỷ và trả hàng loại: L10,L110 |
| Trả một phần | Loại toàn bộ đơn: L10. Trạng thái ghi trên đơn vẫn áp dụng dù phiếu trả sau `as_of_date`: L5 |
| Grain đơn | Mã đơn là khóa khi có; nhóm dòng kế thừa thuộc tính: L108–L109. Không suy một dòng là một đơn. Không giải quyết được khóa thì abstain |
| Dòng trùng | Trùng mọi ô trong cùng đơn chỉ tính một lần; khác đơn tính riêng: L111. Không dùng DISTINCT toàn bảng: L112 |
| Tiền hàng | Cộng thành tiền dòng sau giảm giá dòng; không trừ giảm giá toàn đơn/voucher; không VAT/phí giao: L15 |
| Phí phục vụ | Vẫn tính doanh thu dù không phải mặt hàng để đếm/xếp hạng: L41 |
| Hôm nay/hôm qua | Neo ngày câu hỏi; dữ liệu tương lai chưa xảy ra, ngoại lệ trạng thái trả/huỷ ở trên: L5 |
| Khoảng/ngày gần đây | Hai đầu bao gồm; N ngày gần đây gồm hôm nay: L27–L28 |
| Tuần | Thứ hai đến hôm nay; tuần trước đủ thứ hai–chủ nhật: L30 |
| Tháng | Tháng nêu rõ đủ tháng L31; tháng này đến hôm nay, so tháng trước cùng số ngày và chặn cuối tháng L32 |
| Năm/quý | YTD từ1/1 L33; năm ngầm theo L34, quý dương lịch. Thiếu/không hiểu kỳ thì abstain |
| Thiếu dữ liệu | Không suy thông tin không có L99; kỳ hoàn toàn ngoài dữ liệu không phải0 L100; giao một phần tính phần có dữ liệu L101 |
| Làm tròn | Tiền về đồng, percent2 chữ số L122–L123,L132–L133; trung bình đơn nửa đồng lên L48. Không đổi scorer/provisional policy trong increment này |
| Thay đổi doanh thu | `(asked - previous) / previous * 100`, dấu giảm âm: L19–L20. Không dùng trị tuyệt đối mẫu số |

Phải xác định trạng thái toàn đơn trước khi lọc kỳ; không bỏ dòng trả ở ngoài
kỳ rồi coi đơn vẫn hợp lệ. Join bảng phụ phải có cardinality kiểm được,
không nhân tiền/số đơn bởi nhiều receipts. Raw giữ nguyên; mọi chuẩn hóa có
lineage, duplicate handling tách khỏi dữ liệu vật lý.

Rulebook không nêu riêng cách xử lý baseline0/âm cho percent trong phiên bản
này. v0 chỉ trả khi doanh thu kỳ trước>0; trường hợp còn lại abstain. Không
invent0, vô cực hoặc công thức khác. Những so sánh kỳ chưa kết thúc đã được
L32 định nghĩa thì dùng đúng luật; trường hợp khác không có luật rõ abstain.

## Bộ lọc và ranh giới abstain

Không lọc chỉ được xác nhận sau parser/verifier, không từ heuristic của khảo
sát. Mỗi bộ lọc phải ánh xạ duy nhất tới thực thể/cột có evidence; ưu tiên mã
và alias trong nguồn theo L108. Nhãn ngành phải theo luật ngành L76–L95.
Tên trùng, giá trị không biết, chiều chưa hỗ trợ, phủ định chưa hiểu, loại
trạng thái khác hoặc yêu cầu nhiều kỳ/chia nhóm: abstain, không bỏ lọc.
Không hard-code theo question/business ID. Mã dữ liệu chỉ là khóa, không
phải selector đáp án. LLM không nhận gold/type gold hoặc tự tính số tiền.

## Acceptance trước G2

Mỗi hàm cần synthetic edge tests đúng các định nghĩa trên: trạng thái đủ4loại,
trả một phần sau ngày neo, trùng cùng/khác đơn, nhiều dòng, join một-nhiều,
VAT/ship/discount/service fee, chặn cuối tháng/năm nhuận, ngoài dữ liệu,
lọc không hiểu/không duy nhất; percent thêm baseline0/âm và hai kỳ.

Trên dev cố định: precision=`correct/(correct+wrong)`>=90% ở ít nhất2 cụm
độc lập đã khóa; mỗi cụm đó>=15 câu đã trả lời. N=15 cần>=14 đúng.
Thiếu mẫu báo “chưa đủ mẫu”, không tính đạt, không chia lại cụm và không ép
trả lời để đủ mẫu. Báo correct/wrong/abstain và precision/coverage từng cụm,
cả cụm không có câu; correctness theo scorer dự án, không tự chấm bằng mắt.
Đây là acceptance nội bộ, không tuyên bố ý nghĩa thống kê.

G2 vẫn cần mọi ID hợp lệ có output, PA toàn dev>0 và wrong/answered<=10%,
cùng báo coverage/type/family/business/route/lỗi. Chưa qua G2 chỉ vì một hàm
qua tiêu chí trên. Chỉ dev dùng phát triển; calibration P6 cấu hình cuối/ngưỡng,
holdout P7 một lần, public chỉ smoke/generalization. G5 đã khóa riêng.
