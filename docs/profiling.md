# Profile raw và cấu trúc bảng — A-T2

`datamate profile` tạo thống kê từ cache raw đã xác minh, cùng rule header
thận trọng và data-start. Không đoán kiểu nghiệp vụ, làm sạch hoặc chạy model.
Spec hiện hành: [hoàn thiện A-T2](research/a_t2_completion.md); policy format:
[runtime text/CSV](runtime_format.md). Bản engineering tạm đã lưu trong
[archive GitHub](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/tree/archive/timeline-20261103); dùng spec hoàn thiện trong workspace. Toàn bộ profile chứa mẫu dữ liệu
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
`--no-auto-header` tắt rule để kiểm đối chứng; `--header-scan-rows` mặc định
64, tối đa 256. Codec/delimiter thực dùng và status do loader ghi; profiler
không tự sửa text.

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

## Header, data-start và fallback

SQLite lấy tên/type từ schema khai báo, trạng thái `source_schema`. CSV/XLSX
được rule CPU `header-conservative-1` xem tối đa 64 record raw, budget 1 MiB,
không bị giới hạn 6×32 của preview hiển thị. Rule đòi leaf header có label
dense, anchor ngôn ngữ cột phổ thông, thay đổi dạng giá trị ở hàng sau; nhiều
candidate, nhãn lặp, bảng toàn text không đủ bằng chứng hoặc budget thiếu
trả unresolved. Sparse group header ngay phía trên được giữ thành tập hàng;
title/filter metadata không mặc định là tầng header. Unit rỗng no_header.

Structure giữ version/status/reason/candidate evidence, header_rows và
data_start_row theo tọa độ vật lý. Rule không đọc ID, survey, nhãn benchmark,
README dictionary hoặc header-map train. Không dùng confidence số như bảo
đảm đúng. Không fill merged cells hoặc tạo SQL alias từ label.
Tọa độ dùng đúng __row: XLSX là số hàng worksheet; CSV là record ordinal
(không phải số dòng text nếu có quoted newline), có line_start/end riêng;
SQLite là scan ordinal. Không tự chèn hàng XML bị thiếu.

Descriptor xuất header rows, data-start, header_cells, format/text flags;
unit unresolved còn có bounded row_preview. Có data_samples riêng lấy N
giá trị nonempty distinct từ data-start trong tối đa 128 hàng raw; samples
cũ và thống kê toàn raw giữ nguyên. Data-start chỉ là cận bắt đầu, không
chứng minh mọi hàng sau là giao dịch hợp lệ: totals/notes/duplicates vẫn
có thể nằm trong đó, chưa cleaning.

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

Annotation có thể thêm data_start_row; nếu bỏ qua, lấy hàng nonempty đầu
sau tập header đã khai báo. `rows: []` cùng data_start tường minh biểu diễn
nguồn không header. Annotation là cấu hình dev gắn fingerprint, không có
vai trò nhãn oracle runtime cho business mới. Converter legacy, multi-table
region và cách biểu diễn tối ưu cho LLM vẫn chưa triển khai.

Encoding CSV lấy codec/delimiter đã resolve theo [policy runtime](runtime_format.md).
Text QA chỉ ghi cờ/tọa độ. Rule header có benchmark train cấu trúc dev/check
theo nhóm template/file duplicate; không phải unseen holdout hoặc bằng chứng
PA. Nhãn có README corroboration và self-review, chưa human reviewer thứ hai.

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
