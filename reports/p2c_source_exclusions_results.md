# P2c: áp sáu loại trừ nguồn đã duyệt — 08/11/2026

[Thiết kế](../docs/research/p2c_source_exclusions_design.md),
[plan/ledger](../docs/research/p2c_source_exclusions_plan.md).
Tiếp từ e7e1c6c/PR#8, cùng P2. Người dùng đã duyệt đúng6catalog/payment
sources của2business C3 cho default-unfiltered order_count và revenue_total.
Các nguồn khác và6unknown giữ nguyên, không thêm trạng thái vào core.

## Kết quả audit thật

| Metric | Trước: business / cụm qua kiểm | Sau: business / cụm qua kiểm |
|---|---:|---:|
| order_count | 1 / 1 | **3 / 2** |
| revenue_total | 1 / 1 | 1 / 1 |

Count mở thêm2business C3; business cũ ởC4 vẫn pass, không regression.
Hai business mới vẫn fail revenue vì **amount_format_unverified**, không
thay format/expected hoặc gán tiền0 để cho qua. Blocker nguồn giảm12→10
business; unknown_status vẫn10, resource guard vẫn2. Mọi count/revenue flag
của16business không nhận receipt giữ nguyên. Đối chiếu toàn bộ unit_coverage:
chỉ đúng6unit chuyển disposition, mọi unit chưa duyệt giữ nguyên.

Đây là **machine checks có hỗ trợ source review**, không phải pure-rule binder
tự tổng quát hóa lên3business, không là oracle đáp án, PA hoặc G2. Chỉ6nguồn
được duyệt nghĩa loại trừ; chưa có full-binding independent approval.
Phạm vi filter khác không được thừa hưởng loại trừ hoặc capability này.

## Receipt và guard

- Original packet SHA:
  `ad4d9eac132aa45e9a996bf9ebff8dc95318c5a133971ca4da513ddc944b34fa`.
- Approved artifact SHA:
  `3fd4c1ccfc6f9a143f645424e155d06a15034c0aa2fd3011d3e68b673a1fd032`.
  Artifact/receipt chỉ local trong `runs/p2c-source-exclusions-approved-20261108/`.
- Materialize qua verified reader: packet/proof/schema/columns/row count,
  README quote/hash và raw-file identity khớp. Loader strict bounded JSON,
  SHA/dev/rulebook/receipt/time/đúng cặp metric và scope; duplicate/sai role
  hoặc stale đều bị từ chối. Vẫn là local trust, không chữ ký số người duyệt.
- Matcher kiểm đúng business proof/full-unit SHA/raw/README; chỉ unresolved
  được xét. Nguồn order/header/detail/return/conversion đã nhận diện không
  được dùng receipt để bỏ. Không có rule theo basename/business ID trong code.
- CLI explicit cả --source-exclusions và --exclusions-sha256; diagnose không
  apply.18/18worker nhận cùng source SHA và lexicon SHA đã duyệt.
- Lexicon vẫn SHA `85875bce7d95909cc52e27a5f148393ea04a5c78b6a7b893ab4687b869cd8a30`;
  6unknown và17proposal nguồn còn lại không đổi. Không source auto-discovery.

## Tài nguyên và completeness

Hai ledger mới có128.293–145.479line,33.874–38.499order; dựng ledger10,28–11,86s,
worker18,19–20,97s, peak process243,74–266,65MiB. Đây là full-ledger evidence
trên hai business vừa được mở, không phải business vật lý lớn nhất toàn dev
hoặc benchmark6giờ. Guard row200.000/identity128MiB/DuckDB256MiB/2threads giữ
nguyên; process RSS gồm cả Python/reader/ledger nên khác DuckDB memory limit.

required_row_scan_complete và ledger_validated đều true trên2ledger mới.
physical row_scan_complete false vì6nguồn đã được duyệt loại không bị quét
raw rows; uninspected_units giữ chúng để báo đúng sự thật. Có marker riêng
approved_excluded_units và provenance receipt; không giả full physical scan.

## Lệnh và artifact local

```text
python scripts/p2_binding_audit.py audit
  --profile-index runs/p2c-binding-inputs-20261107/profile/profile.json
  --output runs/p2c-reviewed-source-audit-20261108
  --status-lexicon runs/p2c-status-approved-20261108/lexicon-approved.json
  --lexicon-sha256 85875bce7d95909cc52e27a5f148393ea04a5c78b6a7b893ab4687b869cd8a30
  --source-exclusions runs/p2c-source-exclusions-approved-20261108/source-exclusions-approved.json
  --exclusions-sha256 3fd4c1ccfc6f9a143f645424e155d06a15034c0aa2fd3011d3e68b673a1fd032
```

`comparison-summary.json`, `comparison-local.json` và
`targeted-resource-summary.json` trong output mới lưu delta/identity/resource.
Không đọc gold/calibration/holdout, không gọi model hoặc sửa data/cache/split.
Code digest của proposal thay đổi theo module mới; payload cũ không được tự
tái dùng như evidence model cho code mới.

## Verification và bước sau

TDD:21unit mới RED→GREEN;8case integration từ thiếu kwarg/CLI flags đã
RED→GREEN.55targeted tests pass19,60s; lint/format pass. Review source/synthetic
độc lập45tests pass11,80s, không Critical/Important; không xem real artifacts.
Minor hoãn: thêm test positive CLI worker/parent forwarding; forwarding hiện
đúng theo inspection và18worker thật đã xác minh SHA, chưa có regression
synthetic pin riêng cho đường CLI positive. Không coi source review là PA.

Prerequisite count có machine-checked binding ở2cụm đã mở. Tuy vậy, text
inventory mới chỉ thấy12default-unfiltered ứng viên C3 và8C4, chưa phải
answered và chưa đạt>=15/cụm. Giữ acceptance từng hàm và G2, không gộp revenue
để chứng nhận count. Bước tiếp: parser ý định prompt ngắn/capability verifier,
probe throughput và predict theo thiết kế P2, đồng thời mở thêm scope/binding
có chứng minh để đủ mẫu. Model job sau vẫn cần account/budget mới; không tự
chạy cloud từ receipt nguồn. Docker P3 sau G2.

Full locked CPU sau cập nhật tracker: **603passed/2skipped109,67s**, Ruff
lint/format pass, source không đổi. Đã đọc gate.json và cả ba stage log tại
`runs/cpu-check-20261108T060549767365Z-q29ky47_/gate.json`.
Harness P2 passed/current, không warning/planning error/task active khác,
timeline current; UTF-8/NFC11file và git diff check pass. Không có dependency
mới, không dùng gate cũ hoặc kết quả model cũ để chứng minh increment này.
