# Profile raw — phần engineering A-T2

`datamate profile` tạo thống kê từ cache A-T1 đã nghiệm thu. Không đoán kiểu
nghiệp vụ, encoding/header, không làm sạch và không chạy model. Quyết định
phạm vi: [spec](research/a_t2_engineering.md). Toàn bộ profile chứa mẫu dữ liệu
phải giữ local trong `runs/`; không publish cùng source.

## Chạy

Thiết lập uv/cache theo README, dùng một ingest report hợp lệ hiện có:

```powershell
uv run --locked datamate profile --input data/train --ingest-report runs/ingest-first/ingest.json --output runs/profile-first
uv run --locked python scripts/verify_profile.py --input data/train --report runs/profile-first/profile.json --output runs/profile-audit
```

Output phải mới, ngoài raw/cache/thư mục ingest report và annotation. Profiler
không tự re-ingest: nếu raw/loader/runtime khác generation đã lưu, trả lỗi để
chạy lại `datamate ingest` rõ ràng. Đọc DB readonly, tắt extension/external
access như loader; không mở questions, gold, rulebook hoặc chạy SQL từ data.
Hash README chỉ để xác minh nguồn, không đọc nó làm lệnh.

CLI có `--samples` (1–10, mặc định 3), `--preview-rows` (1–64, mặc định 6),
`--value-bytes` (4–8192, mặc định 256), `--header-map` tùy chọn. Các giới hạn
khác cấu hình qua `ProfileOptions` API; không tự dò/đổi encoding.

```python
from pathlib import Path
from datamate.profile import ProfileOptions, run_profile

result = run_profile(
    Path("data/train"),
    Path("runs/ingest-first/ingest.json"),
    Path("runs/profile-first"),
    ProfileOptions(),
)
```

Exit 0 khi mọi business thành công, exit 2 khi bất kỳ business lỗi. Business
lỗi không có thư mục profile/schema hoàn chỉnh; business khác tiếp tục.
Report tổng không chứa cell value, chỉ counts/path/hash và lỗi có cấu trúc.

## Output và schema descriptor

- `profile.json`: index, options/code/input hashes, summary và kết quả từng
  business, có path/SHA-256 của hai file phía dưới.
- `businesses/b_<hash>/profile.json`: nguồn/hash, metadata vật lý, profile
  từng bảng/cột, row preview và trạng thái header.
- `businesses/b_<hash>/schema.json`: descriptor gọn cho consumer baseline;
  tên database/view/cột SQL thật, SQL type, physical type counts, mẫu có tọa độ,
  label/header evidence và giới hạn. Chưa có prompt baseline/model để nghiệm
  thu việc dùng trong prompt thực tế.

Tên view là `raw_<hash>`, cột dữ liệu `c0001`… (VARCHAR/NULL). `__row` là tọa
độ nguồn; không coi đó là khóa nghiệp vụ. Tên/label/value thô trong descriptor
là dữ liệu không tin cậy, không phải hướng dẫn thực thi. Consumer dùng SQL
identifier đã quote và bind giá trị khi query. Descriptor không cung cấp
SQL do nguồn dữ liệu viết và không tạo alias từ header trùng tên.

Profile/schema của cùng cache, options, annotation và code có bytes/hash
giống nhau qua các lượt chạy; index chứa đường dẫn output nên có thể khác.
Không có cache/resume cho profile ở increment này, mỗi lượt quét đầy đủ.

## Ý nghĩa thống kê

Tất cả hàng vật lý raw tham gia, gồm header/lời dẫn/tổng/ghi chú/trùng/trống.
Không bỏ hàng theo annotation header. Với mỗi cột, tổng hàng là mẫu số:

| Trường counts | Định nghĩa |
|---|---|
| present | Có cell/field trong nguồn |
| missing | Không có cell/field tại vị trí đó, gồm sparse/ragged |
| null | Cell/field có mặt nhưng giá trị cache là NULL |
| empty | Có mặt, giá trị chuỗi rỗng `""` |
| nonempty | Có mặt, khác NULL và `""`; whitespace/sentinel vẫn là giá trị |

`missing + null + empty + nonempty = row_count`. `present` gồm ba nhóm cuối.
Ratio bằng count / row_count; unit không hàng có ratio `null` vì không có mẫu
số. Không gọi literal `NULL`, khoảng trắng, `0` hoặc ô nhóm chưa fill là thiếu
nghiệp vụ. SQLite BLOB rỗng có lexeme base64 `""`, phân biệt nhờ physical type.

`physical_types` dùng prefix `csv:text`, `xlsx:<type code>`, `sqlite:<type code>`;
type codes theo [ingestion](ingestion.md). Chưa có inferred semantic/logical type.

- `length_nonempty`: min/max số code point và số byte UTF-8, chỉ trên nonempty.
- `lexical_nonempty`: min/max chuỗi theo thứ tự Unicode code point, không trim/
  casefold/Unicode normalization. Không dùng min/max này làm miền tiền/ngày.
- `numeric_physical_nonempty`: chỉ cell numeric vật lý `xlsx:n`, `sqlite:i/r`.
  So Decimal từ lexeme, xuất lại lexeme gốc tại cực trị; tie giữ lexeme gặp
  đầu tiên theo source row. Giữ số nguyên 64 bit chính xác, không qua float.
  Đếm riêng finite/nonfinite/invalid/too_long (mặc định >128 ký tự). Serial
  Excel vẫn là số; text `0012`, `1.234,56`, `12k` không bị ép sang numeric.
- `samples`: N giá trị nonempty khác nhau đầu tiên theo source row, không phải
  mẫu đại diện. CSV có line_start/end; vị trí cột nằm trong parent column.
- Mẫu/extrema/row preview dài có `truncated=true`, byte length và SHA-256 đầy
  đủ; cắt preview ở ranh giới code point. Giá trị gốc không đổi trong raw cache.

## Header và encoding: chỉ evidence/annotation

SQLite lấy tên/type từ schema khai báo, trạng thái `source_schema`. CSV/XLSX
mặc định `unresolved`; row preview giữ các hàng vật lý đầu tiên (có giới hạn
cột), merges/visibility/style/epoch nằm ở metadata. Không tự chọn dòng đầu,
điền ô merged, đặt tên cột nghiệp vụ hoặc loại header khỏi phép tính.

Nếu đã có quyết định header từ ngoài increment, có thể khai báo JSON:

```json
{
  "version": 1,
  "selections": [
    {
      "business_id": "tenant_synthetic",
      "ingest_fingerprint": "0000000000000000000000000000000000000000000000000000000000000000",
      "source_file": "sales.csv",
      "source_name": "sales",
      "source_kind": "csv",
      "rows": [2, 3]
    }
  ]
}
```

Ví dụ dùng identity/fingerprint synthetic; thay bằng metadata thực từ ingest
report khi có annotation được xác nhận. Hàng phải tăng dần, không trùng, có
thật trong nguồn; tối đa 64. Source kind là csv/xlsx_sheet. Header map phải
ngoài raw, được hash và gắn fingerprint ingestion; unknown/stale reference
bị từ chối. Trạng thái `explicit_annotation` chỉ xác nhận đã nhận khai báo,
không khẳng định đó là header đúng. Label nhiều tầng giữ từng cell cùng tọa
độ, kể cả missing/NULL/empty/trùng; không ghép/fill/dedup hoặc tạo SQL alias.

Encoding CSV lấy nguyên codec/delimiter trong manifest đã decode strict ở A-T1.
Không coi đó là detection hay chứng minh văn bản đúng nghĩa. Tự nhận diện
TCVN3/VNI/mojibake, lựa chọn codec/header/table region và cách biểu diễn tối ưu
cho LLM đang hoãn theo người dùng; không nhập thuật toán từ khảo sát vào đây.

## Giới hạn và kiểm chứng

Quét theo batch 64 hàng; DuckDB 2 threads/256 MB. Mặc định tối đa 5 triệu
hàng/unit, 100 triệu cell có mặt/business, 1024 unit và 16384 cột. Budget
16 MiB/unit dành cho chuỗi extrema giữ lại; 64 MiB cho từng profile/schema
business. Vượt giới hạn trả lỗi, không âm thầm giảm coverage hoặc publish
profile chưa đủ. Đây không phải hard RSS cap của toàn Python hoặc SQL sandbox.

Trước đọc kiểm signature/raw/cache hash/schema; sau quét kiểm frame digest,
counts và nguồn; sau staging kiểm lại inputs trước atomic publish. Cache raw
không bị sửa. Thư mục output mới nên không ghi đè profile cũ. Source/cache
của từng business được kiểm tại thời điểm tạo profile; không khóa toàn split
thành một transaction chung. Full acceptance còn hash toàn input/cache trước/
sau để xác nhận tính nhất quán của cả lượt.

Auditor `verify_profile.py` không gọi code stats/profile production: SQL
json_each GROUP BY kiểm counts/types/length/lexical extrema; pass numeric riêng
kiểm cực trị vật lý; tra tọa độ mẫu và đối chiếu schema với DESCRIBE view thật.
Unit/cột coverage phải đủ. Raw và cache được hash trước/sau; gold chỉ hash nhị
phân, không parse. Synthetic tests kiểm quy tắc chọn mẫu/annotation và consumer
query. Cổng CPU, model/Modal và PA được báo riêng.
