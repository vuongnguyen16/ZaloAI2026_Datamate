# Nạp dữ liệu raw — A-T1

Loader đọc business từ `<split>/data/<business_id>/`, ghi cache DuckDB ngoài
input. Không mở questions/gold/rulebook để nạp bảng, không gọi model/cloud.
Thiết kế và trade-off: [spec](research/a_t1_raw_loader.md).

## Chạy CLI

Theo thiết lập uv/cache trong README:

```powershell
uv run --locked datamate ingest --input data/train --cache runs/raw-cache --output runs/ingest-first
uv run --locked datamate ingest --input data/train --cache runs/raw-cache --output runs/ingest-second
```

Output report phải là thư mục mới; cache và report phải disjoint với input
và với nhau. Lần hai dùng cùng cache để kiểm tra cache hit; không reparse bảng
khi nội dung/config/code không đổi. `ingest.json` ghi kết quả từng business,
đường dẫn database/manifest, counts, fingerprints và lỗi có cấu trúc.
Exit 0 khi mọi business thành công, exit 2 khi thất bại. Business lỗi không
được publish cache complete; các business khác vẫn được thử.

`--business BUSINESS_ID` có thể lặp để chọn subset. Mặc định nạp tất cả business
trong data/. CSV mặc định strict UTF-8-sig và dấu phẩy theo train; có thể đặt
`--csv-encoding`/`--csv-delimiter` khi đã xác nhận format nguồn. Không dò bằng
decode thay ký tự lỗi hoặc tự đổi số/ngày.

## API và catalog

```python
from pathlib import Path
from datamate.ingest import ingest_business, LoaderOptions
from datamate.ingest.loader import connect

result = ingest_business(
    Path("data/train"),
    "business_id_from_input",
    Path("runs/raw-cache"),
    LoaderOptions(),
)
with connect(Path(result["database"]), read_only=True) as con:
    catalog = con.execute(
        "SELECT source_file, source_name, view_name, row_count FROM __dm_units"
    ).fetchall()
```

Không có business/answer ID được hard-code trong loader. Chọn business từ
input contract; chuỗi trong ví dụ chỉ là placeholder.

Mỗi generation có `raw.duckdb` và `manifest.json`. Catalog trong DB:

| Đối tượng | Nội dung |
|---|---|
| `__dm_sources` | File tương đối, hash, byte size, metadata nguồn |
| `__dm_readme` | README nguyên nội dung sau decode UTF-8-sig; không thực thi |
| `__dm_units` | File/sheet/bảng → storage table/view, counts, width, frame hash và metadata |
| `rows_<hash>` | Frame JSON raw vật lý: `__row`, `__width`, `__payload` |
| `raw_<hash>` | View positional: `__row`, `__width`, `__metadata`, `c0001`… |

`c0001`… là VARCHAR hoặc NULL, không phải tên header nghiệp vụ. Các hàng header,
lời dẫn, tổng, ghi chú, dòng trùng và hàng trống có thật trong nguồn vẫn được
giữ. Không fill nhóm, dedup, gộp sheet hay chọn header ở A-T1. A-T2 sẽ tạo lớp
profile/bản đồ schema với nguồn gốc rõ ràng trên nền raw này.

## Ý nghĩa hàng, ô và kiểu

- CSV: `__row` là record ordinal; metadata giữ dòng vật lý đầu/cuối để phân biệt
  multiline. Trường rỗng là `""`, trường không tồn tại do ragged row là NULL
  khi nhìn qua view; `__width` giữ độ rộng thật. BOM được xử lý bởi codec đã khai
  báo; bytes gốc và hash vẫn ở input/manifest.
- XLSX: `__row` là số dòng worksheet, không tự chèn dòng bị thiếu trong XML.
  Giữ lexeme số/serial, text shared/inline, boolean/error, formula và cached
  value; không tính formula. Metadata nguồn giữ epoch/style XML, metadata unit
  giữ visibility/merge/dimension. Rich text lấy text theo run, không nối thêm
  phonetic annotation. File Excel gốc là nguồn bảo toàn đầy đủ formatting/bytes.
- SQLite: `__row` là scan ordinal, không phải mã nghiệp vụ. TEXT giữ nguyên,
  INTEGER thành chuỗi thập phân chính xác, REAL dùng repr round-trip, BLOB
  base64, NULL giữ NULL. Metadata giữ schema/cột/DDL như dữ liệu và physical type
  từng cell. Không thực thi DDL, view, virtual table hoặc generated column.

Metadata `types` dùng mã gọn, được giải theo source kind. Excel: `n` numeric,
`i` inline text, `s` shared text, `x` cached string, `b` boolean, `e` error,
`d` ISO date text, `-` không có cell. SQLite: `i` integer, `r` real, `t` text,
`b` blob, `0` NULL. Cell missing và cell có mặt nhưng không có cached value có
thể cùng hiện NULL trong view; metadata/width giữ sự khác nhau này.

## Cache và tài nguyên

Cache key gồm business ID, toàn bộ file bảng/README với path/size/hash,
options, hash code loader, phiên bản DuckDB/Python/SQLite. Nội dung giống nhau
trong cùng business có thể dùng lại cache qua vị trí split khác; file paths
trong catalog là tương đối. Khóa giữa business luôn được phân vùng riêng.

Build dùng lock exclusive, staging riêng và atomic rename sau khi kiểm lại
source/code, đối chiếu frame hash sau đọc lại DB và kiểm catalog. Cache hit
kiểm DB SHA-256, signature, catalog và counts/schema. Cache lỗi không bị ghi
đè hoặc âm thầm coi là hit; chọn cache root mới để tái tạo. Lock còn sau khi
process bị dừng đột ngột cần được kiểm tra trước khi dọn, không tự phá lock.

DuckDB dùng 2 threads/256 MB, tắt extension autoload/install. Reader streaming,
spool được dọn khỏi generation; source/cache/report phải tách biệt. Có giới hạn
file/business/XML/ZIP/shared strings/cell/row/column/unit/staging và deadline
SQLite trong `LoaderOptions`. Đây không phải hard RSS cap của toàn tiến trình
Python, hoặc sandbox thực thi SQL do model sinh.

Chỉ đọc bảng SQLite snapshot; sidecar WAL/journal bị từ chối để tránh bỏ sót
transaction khi dùng immutable mode. Input link/junction, nguồn không hỗ trợ,
DTD/entity, relationship worksheet ngoài package hoặc định dạng lỗi trả lỗi
có cấu trúc. Loader hỗ trợ OOXML transitional và strict; không thực thi macro
hoặc external link/formula. Không có fallback âm thầm bỏ bảng.

## Kiểm chứng

Fixture synthetic kiểm tra round-trip cả ba định dạng, NULL/empty/leading zero,
Unicode/quote/newline/NUL, sparse/blank/multiple headers, shared string, styles,
formula/cache/error/hidden sheet, SQLite mixed types/BLOB, cache hit/invalidation,
corruption, source đổi giữa build, lỗi nguồn/limits và alias protection.

Đối chiếu nguồn riêng, không dùng production readers:

```powershell
uv run --locked python scripts/verify_ingest.py --input data/train --report runs/ingest-first/ingest.json --output runs/ingest-audit
```

Audit so từng cell value/type, số dòng/tọa độ/width và unit coverage; hash toàn
raw trước/sau (gold chỉ hash nhị phân, không parse). Không ghi cell value vào
report lỗi. CPU gate và bằng chứng full train phải được báo riêng; không có
model/PA hoặc baseline chất lượng từ loader này.
