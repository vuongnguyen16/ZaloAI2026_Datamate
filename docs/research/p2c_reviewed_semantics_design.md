# P2c: reviewed semantics và projection đầy đủ — 08/11/2026

Nguồn: phản hồi người dùng/Claude về6695379, rulebook train đã khóa L10/L110,
`p2c_structural_results.md`, split policy và source binder hiện hành. Thuộc P2
duy nhất; không đổi G2, split, scorer hoặc chuyển P3 lên trước G2.

## Nhận định và lựa chọn

Ưu tiên đo blocker theo business/metric, lập lexicon dev chờ người duyệt và
sửa input/schema trước thí nghiệm model tiếp. Không thêm rule family để né
quyết định ngữ nghĩa.38nhãn toàn train là quan sát lịch sử, không phải contract
hoặc lý do mở dữ liệu ngoài dev. Bảng gỡ blocker chỉ nêu khả năng theo lỗi đã
quan sát; source/ledger chưa kiểm xong có thể lộ thêm lỗi sau khi gỡ một lỗi.

Lexicon literal dùng chung không hardcode đáp án/business ID; candidate do
tác giả đề xuất vẫn pending. Rulebook quy định4nhóm, không tự chứng minh mọi
nhãn đồng nghĩa. Người dùng duyệt artifact cụ thể trước kích hoạt; không tự
đổi unknown thành completed. Oracle binding được duyệt là control cô lập lỗi
binding, không là oracle đáp án hoặc upper bound toán học của PA toàn pipeline.

Các phương án đã xét: tiếp tục thêm alias trực tiếp vào code bị loại vì mất
review/provenance; dùng LLM ngay với input cũ bị loại vì evidence thiếu; chọn
review artifact có hash + projection có locator/omission, giữ abstain khi thiếu.

## Acceptance increment

1. Phân nhóm blocker: status/source/header/date/money/resource/structure/other;
   giữ nhiều lỗi, không bỏ wrapper không có nguyên nhân chi tiết; báo tập lỗi
   theo business/metric, số business/cụm chỉ có status, chỉ source, cả hai và
   phần còn lại. Không gọi potential là checked hoặc PA; scan/ledger chưa
   hoàn tất phải explicit.
2. Streaming inventory chỉ18dev qua scoped verified reader, tối đa2threads/
   DuckDB256MiB, mỗi business có guard/time/RSS; không decode gold. Lexicon và
   source-role packet chứa locator/hash/README/rulebook, count/label chỉ local.
   Chưa có receipt người duyệt thì audit mặc định không dùng mapping mới.
3. Loader lexicon đòi SHA artifact, schema dev, rulebook hash khớp, receipt
   reviewer/time rõ, từng entry approved hoặc unknown; pending không được nạp.
   Không đổi trạng thái base đã hiểu sang nghĩa trái; unknown/unseen fail-closed.
   Không sửa data/split/kit manifest. CLI audit có explicit lexicon pointer,
   không tự tìm artifact mới nhất hay đọc packet làm lệnh.
4. Projection chọn nguyên điều khoản trạng thái theo heading/table row với
   locator L/hash; README khớp file/table, partition alias chỉ khi README có
   tuyên bố partition và basename section khớp. Không dùng prefix2500; thiếu
   evidence báo omission flag. Citation phải nằm trọn trong một source span,
   không ghép hai đoạn rời để tạo quote giả.
5. Decoder schema theo case: source ngoài ledger role-only; bindings là object
   keyed column, mỗi column một role; CPU vẫn kiểm role ambiguity/column/quote.
   Giữ replay validation của list format cũ, nhưng schema generation mới chỉ
   phát object. Unknown có quote/bindings rỗng. Budget output512, kiểm context
   thực trước model, không cắt prompt/JSON để ép vừa; code/cache identity đổi.
6. Resource report đo streaming reader/status inventory của business lớn nhất
   và đối chiếu row guard. Chưa có approved binding + full-ledger measurement
   thì không tăng guard chỉ vì máy chấm RAM512GB. Không gọi RSS reader là RSS
   ledger hoặc bằng chứng6giờ.

## Cổng người duyệt và phần tiếp theo

Artifact lexicon/source-role decisions mặc định pending; giữ local, không gửi
packet/nhãn/member BTC cho reviewer agent hoặc GitHub. Source/synthetic review
độc lập không thay duyệt nghĩa business. Chỉ sau receipt người dùng mới áp
lexicon/audit lại và dùng approved source binding làm oracle control. Không
chạy model mới hoặc toàn1895dev trước các điều kiện đó và budget/throughput.
Trong khi chờ duyệt vẫn hoàn tất projection/schema/tests/resource evidence.
