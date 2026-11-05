# A-T2 — Spec phần engineering của profile raw

Ngày 05/11/2026. Người dùng chỉ giao phần engineering; hoãn mọi phần research.
Nguồn: timeline DOCX hiện hành A/T2 (hash
e74b1292119f01ca3eae7d20d709921219efc30e655e01909685c50d5363eb51),
docs/requirements.md, docs/ingestion.md và khảo sát A-T1 đã lưu. Note này ghi
quy ước implementation trước sửa kiến trúc, không mở literature/data research.

## Phạm vi và ranh giới

- Quét đầy đủ raw cache đã xác minh; không nạp lại/clean dữ liệu, không mở
  questions/gold/rulebook. Tất cả hàng raw kể cả header/tổng/trùng đều tham gia.
- Đếm từng cột: present/missing, NULL, chuỗi rỗng và nonempty riêng; tỷ lệ có
  mẫu số là tổng hàng vật lý trong unit. Bảng không hàng có tỷ lệ null.
- Giữ SQL type VARCHAR của raw view và histogram kiểu vật lý theo nguồn;
  không suy vai trò nghiệp vụ hoặc logical type từ chuỗi.
- Min/max chuỗi nonempty theo Unicode code point, độ dài ký tự/UTF-8 bytes.
  Min/max số chỉ từ cell numeric vật lý XLSX/SQLite, so Decimal trên lexeme
  đã lưu; không đổi locale, tiền, ngày/serial hay ID text thành số. Token quá
  dài/không finite/không hợp lệ được đếm riêng, không silently coerce.
- Mẫu là N giá trị nonempty khác nhau đầu tiên theo source row, có tọa độ.
  Preview dài bị cắt theo byte UTF-8 ở ranh giới code point, kèm độ dài/hash;
  raw/cache vẫn nguyên. Không tuyên bố mẫu đại diện hoặc tối ưu prompt.
- Header SQLite lấy đúng schema khai báo. CSV/XLSX không chọn header tự động;
  lưu preview đầu unit, merges/visibility và trạng thái unresolved. Cho phép
  annotation hàng header tường minh, gắn fingerprint nguồn, không đưa vào SQL
  identifier, không fill merged cell hoặc loại hàng khỏi thống kê.
- Encoding CSV là codec/delimiter đã khai báo trong manifest loader, không
  gọi đó là detection. Không dò TCVN3/VNI/mojibake hoặc thử/sửa encoding.
- Xuất profile JSON và schema descriptor JSON tất định để baseline dùng tên
  view/cột thật. Chỉ kiểm API bằng consumer synthetic, không chạy baseline/model.

## Thiết kế và phép thử

Chọn `datamate.profile` đọc ingest report + manifest, kiểm nguồn hiện tại,
signature, code/runtime và DB hash/catalog trước đọc cache readonly. Không
sửa module ingest để giữ generation A-T1 hợp lệ. Mỗi unit quét một lần theo
`__row`, kiểm frame digest/counts và cấu trúc payload. Bộ nhớ giữ extrema có
budget; samples/preview/report có giới hạn. Dùng 2 threads/256 MB DuckDB như
loader; không thêm dependency/cloud/model hoặc module rỗng.

Mỗi business có profile/schema JSON riêng publish bằng staging+rename sau
kiểm lại nguồn/DB/manifest/config/code. Report tổng có lỗi cấu trúc và tiếp
tục business khác; output mới, disjoint raw/cache/report/annotation. Không
ghi cell value vào lỗi hoặc log. Dữ liệu mẫu chỉ ở output local ignored.

Các phương án không chọn: suy schema từ sample (không chứng minh full scan),
ép text sang numeric/date (vượt phạm vi), lấy header dòng 1 mặc định (chưa có
quyết định), thêm thư viện encoding/table detection (research đang hoãn).

Acceptance của increment engineering:

1. Fixture ba format chứng minh counts, missing/NULL/empty, physical types,
   extrema, samples, Unicode/leading zero/sparse/formula/empty tables.
2. Header unresolved mặc định; annotation nhiều tầng, header trùng/không đủ
   width có provenance và stale/unknown/invalid annotation bị từ chối.
3. Consumer dùng schema descriptor truy vấn đúng cột raw synthetic; không
   mặc định header là data schema nghiệp vụ hoặc dùng cell làm lệnh.
4. Cache/source/report hỏng hoặc đổi, alias/output overlap và giới hạn có
   failure test; không publish business profile khi fail, không đổi raw/cache.
5. Chạy đủ 30 business/339 unit train; đối chiếu counts/types/null/extrema
   bằng pass riêng; lặp lại output semantic giống nhau; CPU gate current.

Full A-T2 vẫn còn acceptance tự dò encoding/header và dùng trong prompt
baseline thật. Giữ A-T2 in_progress với phần engineering đã nghiệm thu;
research hoãn theo chỉ định người dùng, không đánh dấu toàn task done.

## Kết quả implementation và nghiệm thu engineering

Đã triển khai `datamate.profile`, CLI `datamate profile`, schema descriptor
và `scripts/verify_profile.py`; 28 regression mới. Hai lượt full train đạt
30/30 business, 339 unit, 3.184 cột, 3.997.599 hàng và 33.628.129 cell có mặt;
151.99s và 152.62s. Toàn bộ 60 file business profile/schema giống hash qua hai
lượt. 322 CSV/XLSX units unresolved header, 17 SQLite schema khai báo; không
tạo annotation BTC hoặc thêm thuật toán detection/semantic inference.

Auditor SQL riêng đạt toàn bộ counts/types/length/lexical extrema, pass numeric
vật lý, tọa độ sample và query schema trong 153.29s. Hash 162 raw file và 60
cache file trước/sau không đổi, source không đổi. Không parse gold; không
gọi production profile/stats để tính expected. Artifact:
`runs/a-t2-engineering-20261105/acceptance.json`, `audit/verification.json`.

Cổng CPU exit 0, Ruff/format pass, 115 tests trong 27.51s, không skip;
đã đọc gate/log ở `runs/cpu-check-20261105T062508275441Z-5p01bmls/`.
Source fingerprint trùng full acceptance:
`da548568cc12ebedad7b23f3e4c07b0ce7f8c24a548db20f5863032d8b8847da`.
Self-review xét raw/gold protection, cache/report staleness/corruption,
source đổi lúc scan/staging, sparse/null/empty/physical types, resource bounds
và annotation/label injection. Không agent/người review thứ hai hoặc remote job.

Engineering đã nghiệm thu; A-T2 vẫn in_progress, research deferred_by_user.
Không thay acceptance gốc để coi detection/prompt/model đã xong. Giới hạn và
hướng dẫn: [profiling](../profiling.md); kết quả:
[báo cáo engineering A-T2](../../reports/a_t2_engineering_results.md).
