# P2c: kiểm chứng binding CPU

Ngày 07/11/2026, nhánh `work/p2c-binding-cpu`, từ main `98c1c1e` (PR #5).
**Rule-first v0 chỉ qua kiểm ở 1/18 business dev, thuộc một cụm. P2 chưa qua G2.**
Đây là kết quả kiểm dữ liệu/binding, chưa phải precision, PA hay oracle đã duyệt.

Reader hiện đối chiếu source inventory, cache/catalog, code/runtime,
profile/schema, cột/header và ranh giới dữ liệu trước khi cung cấp iterator.
Rule binder nhận nghĩa cột rõ ràng, kiểm toàn bộ ngày/trạng thái/tiền ở nguồn
được chọn, rồi dựng ledger. Gate đếm đơn độc lập với gate doanh thu. Nguồn
chưa giải thích, trạng thái lạ, scale tiền mơ hồ hoặc vượt guard không được
chuyển thành capability. Chưa nối audit này vào `predict`.

## Kết quả trên dev

| Cụm | Business | Qua kiểm đếm đơn | Qua kiểm doanh thu |
|---|---:|---:|---:|
| C1 | 5 | 0 | 0 |
| C2 | 7 | 0 | 0 |
| C3 | 3 | 0 | 0 |
| C4 | 3 | 1 | 1 |
| Tổng | 18 | 1 | 1 |

| Kết quả / lý do chính | Business |
|---|---:|
| Qua kiểm máy | 1 |
| Có nguồn liên quan chưa bind / chưa chứng minh được phép loại | 13 |
| Có phần nguồn cùng họ chưa bind | 1 |
| Không qua kiểm dữ liệu | 2 |
| Không có candidate đủ điều kiện | 1 |

Hai business không qua kiểm dữ liệu đều có trạng thái chưa map; một business
đồng thời không qua screen số học. Không suy nghĩa nhãn lạ bằng tần suất và
không bỏ nguồn chỉ vì tên file có vẻ là bảng phụ. V0 chưa giải các layout
header/detail và các bảng phụ ngoài signature quy đổi đóng. Các số trên đo
độ bảo thủ của binder v0, không kết luận 17 business còn lại không thể bind.

Tác giả đã đối chiếu mapping candidate qua kiểm với định nghĩa README,
header, ba dòng mẫu, inventory trạng thái/format và diagnostic ngày cuối.
Đây là **author check**, chưa phải kiểm độc lập binding business thật.
Packet local vẫn chờ người duyệt; screen số học không chứng minh nghĩa net,
và những dòng không khớp số học chưa được duyệt riêng từng dòng.

Vì chỉ một cụm có business qua kiểm, đường trả lời dựa trên binding hiện tại
chưa thể đạt acceptance mỗi hàm đúng trên ít nhất hai cụm. Không dùng taxonomy
để đổi số candidate thành số câu sẽ trả lời. Chưa chạy 1.895 câu dev, chưa mở
gold mới, calibration/holdout vẫn kín; không có model/cloud job trong increment.

## Provenance và tài nguyên

Lượt đầu `runs/p2c-binding-audit-20261107/` bị `stale_ingest_identity` ở cả18
business trước binder. Hash code ingest cũ khớp chính xác `790b1af`, khác code
hiện tại; không phải chỉ do LF/CRLF. Giữ nguyên lượt lỗi và mọi cache cũ.
Không nới guard, không sửa source/manifest/hash để ép dùng lại generation.

Dựng mới chỉ18 business dev đã authorize, giữ options ingest/profile cũ:
`runs/p2c-binding-inputs-20261107/`. Profile mới valid18/18,212unit,
2.797.749 hàng vật lý;8header unresolved được giữ nguyên. Audit thực:

```powershell
.venv/Scripts/python.exe scripts/p2_binding_audit.py audit --profile-index runs/p2c-binding-inputs-20261107/profile/profile.json --output runs/p2c-binding-audit-20261107-v2
```

Artifact local: `summary.json`, `businesses-local.json`, từng `binding.json`,
`review-packet-local.md` và `author-review-local.json`. Không đưa packet,
business membership, dữ liệu nguồn hay gold lên GitHub/reviewer agent.

Tổng elapsed trong18 worker là55,84giây, không gồm thời gian dựng cache/profile,
authorize/startup của parent. Business duy nhất dựng được ledger có56.501dòng,
22.428đơn; dựng ledger12,75giây, tổng worker25,28giây, peak RSS142,84MiB.
RSS là peak cả vòng đời process, gồm Python/DuckDB/xác minh artifact, không phải
bộ nhớ riêng ledger. Chưa dựng ledger ở business lớn nhất toàn dev; không
ngoại suy thành bằng chứng ngân sách6giờ. Mỗi child2threads, DuckDB256MiB,
timeout90giây; guard rows/estimated bytes không là OS memory limit.

## Hai lượt review source và synthetic

Reviewer không đọc kit/gold/packet thật. Lượt1 có4Important đã tái hiện rồi sửa:
file nguồn thêm mới không được phát hiện; profile có thể thiếu unit/cột;
nguồn khác họ/trả hàng có thể bị bỏ qua; định nghĩa net theo prefix nhận cả
VAT/ship/voucher. Regression cũng kiểm header vật lý/declared column và
trường hợp chỉ một dòng số học phân biệt scale tiền.

Lượt2 có3Important, đều có regression RED→GREEN:

- Profile tự nhất quán nhưng đẩy `data_start_row` xuống làm mất đơn: đối chiếu
  tọa độ header và hàng không rỗng đầu tiên sau header; SQLite phải bắt đầu từ1.
- Header quen thuộc che README mô tả nghĩa khác: định nghĩa mâu thuẫn hoặc
  chưa hiểu phải veto; không dùng label để vượt mô tả có sẵn.
- Sai vocabulary header: dùng đúng `auto_rule`, `source_schema`,
  `explicit_annotation` từ producer, có kiểm thêm pipeline SQLite thật synthetic.

Việc sửa boundary cũng làm annotation cố ý bỏ hàng không rỗng sau header
chưa được v0 chấp nhận. Đây là giới hạn bảo thủ được ghi trước dùng binding.
Không còn minor hoãn. Hai lượt review độc lập source không thay việc duyệt
mapping business thật. Trust root vẫn là split/source/code và artifact local;
không có chữ ký độc lập chống thay đồng thời mọi artifact, hay OS isolation
chống process thù địch thay filesystem trong lúc đọc.

## Việc tiếp theo

Tiếp tục một increment P2c CPU: giải thích các nguồn chưa bind và chốt layout
header/detail/bảng phụ hoặc nhãn trạng thái có nguồn nghĩa rõ, ưu tiên business
thuộc cụm thứ hai. Duyệt binding bằng evidence, giữ per-metric gates riêng.
Sau đó mới adapter ý định ngắn, probe throughput cấu hình sát chạy thật và
full-dev evaluation. Không tăng coverage bằng cách bỏ guard hoặc đọc gold vào
inference. Billing thực Modal vẫn chưa có số dashboard.

CPU cuối **509 passed, 2 skipped trong154,59giây**, Ruff lint/format pass,
source không đổi; đã đọc gate.json và ba stage log:
`runs/cpu-check-20261106T200626300303Z-p8p_2mc9/gate.json`.
Fingerprint `ab8475b058e3dfd7e4539df219dfb0ba3dd3542598871c81ddf28abd0b6c8379`.
CI nhánh kiểm riêng; CPU không chứng minh model hoặc PA.

Các quyết định của tác giả trong increment: giữ hai lượt review theo yêu cầu;
nâng kiểm số dòng phân biệt scale thành điều kiện an toàn; dựng cache mới
thay nới identity guard; tách kiểm máy/author check khỏi oracle và PA; giữ
upstream loader/profile/split trong trust hiện có; không tuyên bố OS isolation
hay chống thay đồng thời toàn bộ provenance. Đổi lại có thêm thời gian/dung
lượng CPU và nhiều trường hợp abstain; lỗi mapping, upstream hoặc can thiệp
thù địch vẫn là rủi ro ngoài bằng chứng hiện tại.
