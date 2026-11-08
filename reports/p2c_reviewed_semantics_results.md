# P2c: semantic review và sửa proposal — 08/11/2026

Increment trên `work/p2c-structural-binding`, tiếp từ6695379/PR#7.
[Thiết kế](../docs/research/p2c_reviewed_semantics_design.md),
[plan và ledger](../docs/research/p2c_reviewed_semantics_plan.md).
P2 vẫn là task active duy nhất; chưa PA/G2, P3 sau G2.

## Nhận định

Đồng ý ưu tiên blocker riêng, lexicon người duyệt và sửa input trước model.
38nhãn toàn train là quan sát lịch sử; lần này chỉ inventory dev được phép.
Không kết luận gỡ một blocker sẽ pass các kiểm chưa chạy. Oracle binding do
người duyệt là control tách lỗi binding, không phải oracle đáp án hoặc upper
bound toán học của PA. RAM512GB máy chấm không chứng minh guard local an toàn.

## CPU dev inventory và review packet

Lệnh:
`python scripts/p2_semantic_review.py prepare --profile-index runs/p2c-binding-inputs-20261107/profile/profile.json --audit-records runs/p2c-semantic-default-audit-20261108/businesses-local.json --output runs/p2c-semantic-review-20261108-v3`.

18dev, 212source units; inventory hoàn tất trên các cột trạng thái order đã
nhận diện ở18/18business, thu29nhãn literal. Không chứng nhận nhãn nằm trong
nguồn chưa xác định vai trò. Mỗi source đều có entry để duyệt, kể cả source
không được quét status. Không đọc gold hoặc inventory calibration/holdout.

Packet chỉ local trong thư mục output: `review-packet-local.md`,
`lexicon-review.json`, `source-review.json`, `inventory-local.json`,
`blockers-local.json`, `summary.json`. Không publish packet/nhãn/member BTC.
Tất cả entry pending; target runtime unknown. Candidate dùng lexicon cũ hoặc
tên literal của4nhóm; nhãn chưa đủ nghĩa giữ unknown. Rulebook/README có
trích dẫn, hash, dòng nguồn; rulebook định nghĩa nhóm, không chứng minh mọi
đồng nghĩa. Source packet có chỗ điền role/column/join và relevance từng metric.

Audit mặc định mới vẫn count/revenue1/18, một cụm. Phân nhóm observed blocker
trên lượt này (không mô phỏng pass):

| Tập blocker duy nhất đã ghi nhận | order_count: business / cụm | revenue_total: business / cụm |
|---|---:|---:|
| Chỉ status | 4 / 2 | 1 / 1 |
| Chỉ source | 1 / 1 | 1 / 1 |
| Cả status và source, không có nhóm khác | 3 / 2 | 1 / 1 |
| Còn blocker nhóm khác | 9 / 3 | 14 / 4 |
| Đã qua kiểm mặc định | 1 / 1 | 1 / 1 |

Các nhóm còn lại giữ header/date/money/resource/structure/other.17business
chưa đủ bằng chứng scan/ledger; không suy rằng29nhãn sẽ mở khóa chúng.
Code giữ cờ scan và ledger riêng, liệt kê source chưa quét; mọi counterfactual
cho business chưa pass bắt buộc recheck. Số cụm giữa các bucket có thể trùng.

## Ranh giới áp dụng

Audit mặc định giữ STATUS cũ. Chỉ opt-in bằng cả `--status-lexicon` và
`--lexicon-sha256`; loader kiểm artifact SHA, dev scope, rulebook hash,
receipt reviewer/time, từng entry approved/unknown và xung đột nghĩa base.
Pending/stale/nhãn mới không được tự chấp nhận. SHA/receipt là quy trình
review local, không phải chữ ký xác thực danh tính người duyệt.

Chưa có receipt người dùng: chưa áp lexicon mới, chưa dùng source packet làm
oracle binding, chưa chạy oracle-control PA hoặc gọi lại model. Nối oracle
runtime phụ thuộc quyết định role/column/join cụ thể và CPU invariants; packet
pending không phải capability chạy ledger.

## Proposal input và decoder

- Chọn nguyên điều khoản trạng thái/metric liên quan (kể cả cuối rulebook),
  bỏ fallback prefix2500. README theo file/table, partition alias chỉ có khi
  README tuyên bố tách file và section basename tồn tại.
- Projection v2 có locator/hash/omission/missing flag; quote phải nằm trong
  một span. Không chấp nhận quote ghép xuyên hai đoạn rời.
- Schema theo case, bindings object keyed column; source ngoài ledger chỉ
  role, không bind cột. CPU vẫn veto trùng role, quote/cột lạ. Giữ validation
  list cũ để replay, schema generation mới dùng object.
- Output budget riêng512token, không đổi256token của intent probe; giữ kiểm
  tổng context trước generate. Code/projection/model/rulebook đổi cache key.

Kiểm CPU không chứng minh decoder tương thích runtime GPU hoặc chất lượng
model. Chỉ chạy proposal mới sau review oracle và account/budget mới; không
tái dùng số liệu13generation cũ để đánh giá input mới.

## Tài nguyên

Business có nhiều dòng vật lý nhất:289.369dòng, inventory đọc78.850dòng status,
1.75s, peak process127.03MiB. Business đọc status nhiều nhất:103.720dòng,
5.26s, peak106.48MiB. Đây là streaming reader/status inventory trong worker
riêng, không materialize ledger; không chứng minh peak ledger hoặc6giờ.
Giữ guard200.000dòng/128MiB và budget DuckDB256MiB/2threads. Full-ledger
measurement trên nguồn lớn còn phụ thuộc approved binding.

## Verification và phần chờ

Targeted tests:40pass sau một fix pass. Review source/synthetic độc lập phát
hiện3Important (SQLite nhầm file, hash README normalized, source packet thiếu
rulebook) và1Minor về bucket còn lại, tác giả nâng Important do thiếu tổng
business bị chặn.5regression mới đã RED→GREEN; không minor hoãn. Review không
đọc raw/gold/packet thật và không thay thế người duyệt ngữ nghĩa.

Full locked CPU: **574passed/2skipped,158,76s**; Ruff lint/format pass,
source không đổi trong gate. Đã đọc gate.json và ba stage log:
`runs/cpu-check-20261108T045459818853Z-429czhr5/gate.json`.
Timeline check current; UTF-8/NFC23file và git diff check pass. Model/PA chưa
đo trong increment này; kill/resume test gốc pass, không đổi timeout/expected.

Thứ tự còn phụ thuộc người duyệt: duyệt lexicon → audit thật lại → duyệt source
role/column/join → oracle binding control (ghi riêng, không G2) → đo proposal
đúng/sai/unknown trên oracle → intent/throughput → full dev khi đủ điều kiện.
Không chuyển P3 lên trước G2 hoặc nới guard theo RAM danh nghĩa.

CPU prepare payload mới: 16case ({'source': 8, 'status': 8}); missing evidence=2, omission disclosed=16. Artifact chỉ local `runs/p2c-proposal-payload-20261108-reviewed-v2/`, identity khớp code cuối; chưa gọi model.
