# A-T1 — Spec loader raw và cache theo business

> Bằng chứng module được giữ từ các phiên A-T1/A-T2 trước migration. Tham chiếu tuần, hash kế hoạch và handoff bên dưới là lịch sử; kế hoạch hiện hành là P0–P9 trong [state](../project_state.md) và [backlog](../../tasks/backlog.json).

Ngày 05/11/2026; người dùng đã giao triển khai loader/cache sau khảo sát sâu.
Nguồn kế hoạch: timeline DOCX hiện hành A/T1, hash
e74b1292119f01ca3eae7d20d709921219efc30e655e01909685c50d5363eb51.
Contract: docs/requirements.md và manifests/competition_contract.json.
Nguồn thực nghiệm: a_t1_deep_survey.md, artifacts local cùng tên.

## Quyết định cần thử trước triển khai

Mục tiêu là nạp được và truy vấn dữ liệu nguyên trạng. Không đoán header, không
parse tiền/ngày, fill nhóm, gộp sheet, đổi status hoặc dedup trong increment này.
Các hàng header/lời dẫn/tổng/trống vẫn là hàng raw; profile A-T2 sẽ phân vùng sau.
Không đọc questions/gold/rulebook để nạp bảng; chỉ đọc thư mục business và README.

**Phương án chọn:** mỗi business có một DuckDB, mỗi nguồn CSV/sheet XLSX/bảng
SQLite có bảng riêng. Tên bảng sinh từ hash định danh nguồn, cột dữ liệu theo
vị trí c0001…; không dùng header thô làm SQL identifier. Từng hàng có số thứ tự
nguồn, chiều rộng thực và metadata cell. Mọi scalar lưu VARCHAR hoặc NULL;
metadata giữ kiểu vật lý, style/formula cần thiết để diễn giải sau. Với SQLite,
INTEGER biểu diễn thập phân chính xác, REAL dùng repr round-trip, BLOB base64;
không ép TEXT giống số thành số. Giữ schema SQLite và thứ tự cột riêng.

XLSX đọc OOXML streaming bằng thư viện chuẩn: giữ lexeme số/serial, chuỗi
shared/inline, boolean/error, formula và cached value, tọa độ, row attributes,
style reference, workbook epoch/style XML, visibility/merge/dimension metadata.
Không tính formula, không đọc external relationships ra ngoài package. File gốc
và hash là nguồn bảo toàn đầy đủ bytes/định dạng; cache không thay file Excel.

CSV đọc strict bằng Python csv, encoding UTF-8-sig/delimiter ',' mặc định theo
train, có cấu hình explicit. Giữ whitespace, Unicode, leading zero, trường rỗng,
độ rộng ragged và số dòng nguồn. Không thử encoding bằng errors=replace.
SQLite mở URI read-only/immutable, query_only/trusted_schema off; từ chối sidecar
WAL/journal, view/virtual table thay vì âm thầm bỏ qua hoặc thực thi SQL từ data.

Để tránh executemany hàng triệu lần, staging CSV do chính loader ghi trong cache
temp: chuỗi luôn quoted, NULL unquoted rỗng. DuckDB đọc explicit schema VARCHAR,
auto_detect=false, allow_quoted_nulls=false, strict_mode=true, không skip lỗi.
Spool gồm JSON sparse theo hàng và một lần copy sang bảng có cột positional;
spool/temp ngoài input, dọn khi hoàn tất. DuckDB 2 threads, 256 MB.

Refinement sau probe: lưu payload JSON nguyên giá trị trong bảng vật lý có
row/width, rồi tạo view positional c0001… bằng json_extract_string. Như vậy
không cần re-encode ragged row thành một CSV rộng lần hai, phân biệt missing/
NULL/empty nhờ payload và metadata, và có thể kiểm digest read-back nguyên
frame. View là SQL do loader sinh từ chỉ số/hash, không lấy SQL từ dataset.
Trade-off là chi phí JSON extraction khi query; A-T2/baseline sẽ đo tiếp trước
khi quyết định materialize lớp profile/clean. Probe đã pass NULL/empty/leading
zero/literal NULL/newline/NUL trên DuckDB 2.0.0; dùng SQL read_csv với binding
path vì Python wrapper 2.0 không nhận alias nullstr.

**Phương án khác:** auto-infer schema/header nhanh nhưng làm mất ID/lexeme và
nhầm header; openpyxl/pandas tiện nhưng convert ngày/số, cần thêm dependency;
executemany thuần dễ viết nhưng cần đo throughput; JSONL staging giữ NULL dễ hơn
nhưng rộng và tốn parse. Không thêm dependency cho OOXML trước khi có nhu cầu.

## Cache, lỗi và tài nguyên

Fingerprint chứa business ID, danh sách path/size/SHA-256 của README và mọi file
bảng, config/limits, loader code hash và runtime ảnh hưởng kết quả. Không chứa
gold hoặc nội dung câu hỏi. Nội dung nguồn đổi, config/code đổi hoặc danh sách
file đổi phải ra generation mới. Cache hit kiểm hash DB và catalog/schema/counts;
cache hỏng báo lỗi, không coi là hit. README được cache như dữ liệu, không là lệnh.

Build dùng lock exclusive và thư mục staging riêng; chỉ publish generation sau
khi đọc đủ mọi nguồn, kiểm lại fingerprint nguồn và đóng DB. Business lỗi không
được có cache complete; báo lỗi cấu trúc có code/business/file/unit/row khi biết.
Split tiếp tục business khác và valid=false nếu bất kỳ business lỗi. Không log
cell value/SQL nguồn trong thông báo lỗi mặc định. Không ghi đè cache cũ/raw.

Output/cache phải disjoint input, kiểm resolved path/junction/symlink và path
traversal. Chỉ đọc file trong business, từ chối nguồn không hỗ trợ hoặc symlink.
ZIP/XML có giới hạn kích thước/package/cell/row/column, không DTD/entity, không
extract archive. Giới hạn row/column/staging bytes và SQLite deadline; không
autoload/install extension, không remote job. Cache là artifact local tin cậy,
hash bảo vệ corruption, không phải chữ ký chống người sửa cả DB lẫn manifest.

## Phép thử và acceptance

1. Probe trên duckdb 2.0.0 đã khóa: phân biệt quoted empty, NULL, literal NULL,
   leading zero, quote/newline/NUL; so giá trị đọc lại với đầu vào synthetic.
2. Fixture synthetic có ragged CSV/multiline/BOM, header nhiều tầng, row trống,
   sparse cell/shared string/style/serial/formula/error/hidden sheet, SQL types
   mixed/BLOB/NULL/quote identifier. So toàn row/cell/provenance, hash raw bất biến.
3. Lỗi encoding/ZIP/XML/SQLite/view/limits và thay nguồn giữa build không tạo
   complete cache; không đọc gold, không input alias/output trùng/hardlink mutation.
4. Cache hit không reparse bảng; thay table/README/config/code làm invalidation;
   cache hỏng/busy được báo đúng; tên file/sheet/header không gây SQL injection.
5. Full train: đủ 30 business/128 file bảng/339 unit; đối chiếu row counts và
   digest values theo từng unit với một pass đọc riêng, không dùng gold. So với
   survey: 3.997.518 nonempty rows; raw reader còn giữ các row trống vật lý.
6. CPU gate cuối pass và current; model/PA không chạy. Self-review được ghi rõ.

## Nguồn kỹ thuật và trạng thái

- [DuckDB 2.0 CSV options](https://duckdb.org/docs/2.0/data/csv/overview.html):
  explicit columns, tắt autodetect, quoted-null behavior và order preservation.
- [Python 3.11 SQLite](https://docs.python.org/3.11/library/sqlite3.html):
  URI mode=ro và kiểu Python native.
- [Python 3.11 ElementTree](https://docs.python.org/3.11/library/xml.etree.elementtree.html):
  iterparse và lifecycle element; bộ đọc có giới hạn và từ chối DTD.

Tra cứu hẹp bằng TinyFish search/fetch; không dùng deep research trả phí.
Các lựa chọn trên là quy ước nội bộ của lớp raw, không thay đổi contract BTC.
Kết quả nghiệm thu implementation được ghi riêng bên dưới và trong
[báo cáo A-T1](../../reports/a_t1_loader_results.md).

## Implementation và bằng chứng nghiệm thu ngày 05/11

Đã triển khai module `src/datamate/ingest/`, CLI `datamate ingest`,
`scripts/verify_ingest.py` và 28 regression ingest synthetic. Hướng dẫn API,
catalog, physical type codes, cache và giới hạn: [ingestion](../ingestion.md).

Full train đã nạp đủ 30 business/128 file bảng/339 unit vào 30 DuckDB; giữ
3.997.599 hàng vật lý, gồm 3.997.518 nonempty và 81 hàng trống XML hiện diện.
Cold build 374.85s; warm ban đầu 3.50s, warm cuối 3.67s với 30/30 cache hits.
Đối chiếu riêng toàn cell value/type/tọa độ/width/counts/unit coverage đạt
339/339 unit; lượt cuối 241.32s. Hash 162 file raw và code loader không đổi
trong các lượt; không parse gold. Cache DB tổng 312.320.000 bytes.

Artifact local:
`runs/a-t1-loader-acceptance-20261105T050128Z-j5zoovbj/acceptance.json`,
`final_acceptance.json`, `final-audit/verification.json`. Auditor cuối có
regression CSV 150.000 ký tự, dùng giới hạn manifest và khôi phục parser limit;
không cần đổi loader/generation từ cold build. Full audit cuối và CPU gate
cùng source fingerprint
`1980a674cc985b88560a1c67a9ab907289069e41822e8e68cee335a4c39d59ce`.

Cổng `uv run --locked python scripts/check.py` đạt exit 0, Ruff/format pass,
87 tests trong 15.77s, không skip/source mutation; đã đọc JSON và log ở
`runs/cpu-check-20261105T051420112942Z-h48l958o/`. Review bởi tác giả, tập
trung raw/leakage, failure isolation, cache invalidation/corruption, lifecycle
SQLite/stream, path/junction và resource bounds. Parser audit độc lập là
phép kiểm riêng, không phải review bởi agent/người thứ hai.

Các giới hạn spec giữ nguyên: JSON extraction cần đo ở A-T2/baseline; không
hard RSS cap toàn Python, không model-SQL sandbox, không tự phá stale lock;
SQLite view/virtual/generated/WAL bị từ chối; cache không thay toàn bộ bytes
Excel hoặc xác thực manifest chống sửa ác ý. Không thêm cleaning/schema
inference vào raw. Không Modal/model/PA/Docker hoặc thay dependency/contract.
Acceptance A-T1 đã đạt; A-T2 vẫn todo, sẵn sàng ghi spec profile/header.
