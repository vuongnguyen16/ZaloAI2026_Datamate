# P2c: đếm ứng viên order_count theo text — 08/11/2026

[Assessment](../docs/research/p2c_count_feasibility_review.md).
P2 active duy nhất; không sửa code inference/core/scorer hoặc split.

## Merge PR#7

[PR#7](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/pull/7) đã merge
thành `aee0785efc33699879d770dc1789200a5a0790d4` sau chỉ dẫn merge khi CI xanh.
Đã xác minh head `d5c9ea2`, không unresolved thread/review; [CI run48](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/actions/runs/42449917024)
completed/success, job/step/log đã đọc: Ruff/format pass, **576passed35,18s**
trên Ubuntu. API merge có expected_head_sha để từ chối nếu nhánh đổi.
Follow-up này trên nhánh riêng từ origin/main sau merge; không tự merge tiếp.

## Phương pháp CPU/no-gold

Lệnh local thực: `python runs/p2c-count-text-feasibility.py`,
`python runs/p2c-count-scope-text-review.py`,
`python runs/p2c-count-missed-signal-check.py`.
Script/artifact/câu hỏi/member/ID chỉ local dưới
`runs/p2c-count-feasibility-20261108/`.

Scoped reader decode1895câu dev/18business;1105record ngoài dev chỉ route,
không decode value. Không đọc gold type/answer, không tái chạy taxonomy có
gold. Classifier nhận text và placeholder expected_type; không dùng số135
từ các ô taxonomy cũ như một phép đếm scope đã xác nhận.

Heuristic hiện hành:203primary-family order_count,217có tín hiệu count.
Tách217text thành105ứng viên đếm đơn mặc định không lọc,75câu hỏi số đơn
huỷ,12entity/shift flags,7comparison/ratio,10amount/other filter,6đếm thực
thể khác,2ranking. Tác giả đã đọc lại cả217text và56supplemental matches
ngoài classifier; không thấy thêm default-count trong56đó. Vẫn có rủi ro
bỏ sót phrasing ngoài pattern, chưa human-review độc lập toàn corpus.
105là ứng viên text, không là supported/answered hoặc cận trên toàn bộ dev.
Kỳ, typo, dữ liệu, bộ lọc và verifier thực còn có thể làm abstain.

## Các nhóm ứng viên sau lexicon

| Cụm | Business đã qua binding: ứng viên mặc định | Source-only: ứng viên | Status-only: ứng viên | Source+status-only: ứng viên |
|---|---:|---:|---:|---:|
| C1 | 0 | 0 | 21 | 0 |
| C2 | 0 | 3 | 0 | 10 |
| C3 | 0 | 12 | 0 | 0 |
| C4 | 8 | 0 | 11 | 0 |

Các nhóm blocker khác còn40ứng viên mặc định. Toàn dev theo cụm là40/25/21/19.
Bảng đầy đủ theo từng business, gồm tín hiệu thô, scope bucket và câu hỏi,
ở `scope-review-local.md`, `scope-businesses-local.json`; không xuất lên Git.

Riêng3business source-only ở2cụm: C2 có3câu; C3 có5+7=12câu. C4 đã qua
binding có8. Vì vậy duyệt23nguồn là bước mở binding đáng làm, nhưng **chưa
có cơ sở hứa đạt>=15answered ở2cụm** cho hàm hiện tại. Nhãn count thô của
nhóm này còn chứa câu đếm đơn huỷ, tiền hàng tối thiểu, đếm khách hoặc ca.
Không bỏ điều kiện của câu hỏi để tăng coverage.

Nếu chỉ xét các ứng viên đã nhận diện và giả sử cả source-only/status-only
được giải, C1 có21 và C4 có19; C2 chỉ3, C3 chỉ12. Đây là scenario chẩn đoán,
không phải kết quả ledger hoặc PA. Không tự thay acceptance; gộp câu revenue
không chứng minh mẫu cho order_count vì acceptance nội bộ là per-function.

## Author review nguồn và nhãn: chưa kích hoạt

Đã đọc23nguồn trong packet ưu tiên và bổ sung role/rationale/proposal riêng
cho order_count/revenue_total với scope unfiltered:
16nguồn đề xuất loại theo scope,2nguồn bắt buộc header/detail,2required-review,
2metric-specific,1phải reconcile. Trong đó thẻ kho có chứng từ trả hàng được
giữ để reconcile; chi tiết lô/returned quantity chưa đủ semantics giữ unknown,
không tự loại. Proposal cần CPU/full-row/cardinality và receipt trước dùng.
Nguồn payment/catalog có thể cần lại khi hỗ trợ filter; không loại toàn cục.

Hai packet local mới: `source-author-proposals-local.md/.json` và
`binary-status-proposals-local.md/.json`. Sáu nhãn trong lexicon đã duyệt
vẫn unknown, SHA artifact không đổi. Bảng nhị phân chỉ đề xuất1nhãn theo nghĩa
trả→returned hiện hữu,5nhãn còn có thể là trạng thái được tính. Một thay đổi
này riêng lẻ cũng chưa gỡ unknown cho business nào trong inventory, vì những
business chứa nó còn nhãn mơ hồ khác. Chưa xin/chuyển receipt cho thay đổi đó.
Không thêm trạng thái thứ5, không có model/oracle-control hoặc audit mới.

## Acceptance và verification

Đã làm rõ câu chữ note binding: không đặt minimum15 cho audit binding;
minimum15answered/cụm, precision>=90% ở>=2cụm vẫn là acceptance PA nội bộ
**từng hàm** theo domain_scope. G2 toàn dev vẫn theo quyết định06/11.
Quy tắc4canonical status, nguồn rulebook, split và scorer giữ nguyên.

Các packet thật giữ local.

Full locked CPU cuối: **574passed/2skipped131,95s**, Ruff lint/format pass,
source không đổi; đã đọc gate.json và ba stage log tại
`runs/cpu-check-20261108T054029635743Z-betocitb/gate.json`.
Harness P2 passed/current, timeline current, không warning/planning error/
task active khác. Fingerprint so với gate trước chỉ đổi backlog, không có
code runtime mới. Kiểm chéo1895record unique/18business,217signal và105scope
candidates khớp giữa bảng theo câu và theo business. Lexicon SHA/6unknown
được kiểm lại, không đổi.

Đã tách thêm `source-c3-review-local.md/.json`:6catalog/payment sources của
2business C3, đề xuất loại chỉ cho default-unfiltered hai metric; các nguồn
và semantics khác giữ pending. Packet tập trung có README/rulebook quote,
locator/hash; chưa phải receipt hay CPU capability. Đây là quyết định nguồn
mới, không nằm trong lần người dùng duyệt lexicon.
