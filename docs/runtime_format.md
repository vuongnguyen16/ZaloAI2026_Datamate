# Runtime text/CSV policy — hoàn thiện A-T2

Policy version 1 trong `datamate.ingest.text_format`. Mặc định CLI
`--csv-encoding auto --csv-delimiter auto`; resolve theo từng file, không
cần có người khai báo cho business mới. Raw không bị ghi lại/chuyển mã.

## Byte decoding

1. BOM UTF-8, UTF-16LE hoặc UTF-16BE: decode strict tương ứng và bỏ BOM.
2. Không BOM: strict UTF-8. Phân biệt empty, ascii_only, utf8_validated.
3. Codec explicit được ghi configured_override; BOM xung đột bị từ chối.
   Không fallback cp1258/cp1252/latin-1 chỉ để decode “thành công”.
4. Invalid bytes trả lỗi cấu trúc với encoding_status=undecodable. UTF-32 BOM
   hiện unsupported và bị từ chối rõ. README dùng cùng BOM/UTF-8 policy.

Metadata `encoding` là codec thực dùng; `encoding_status` gồm `bom_utf_8`,
`bom_utf_16_le`, `bom_utf_16_be`, `empty`, `ascii_only`, `utf8_validated`,
`configured_override`; `bom` giữ loại BOM hoặc null. Decode thành công không
chứng minh văn bản đúng nghĩa. UTF-16 không BOM có thể chứa bytes UTF-8 hợp
lệ (NUL), nên không tự đoán là UTF-16; QA chỉ gắn cờ NUL. Không sửa legacy,
mojibake, normalization hoặc ID/text.

## Delimiter

Explicit delimiter dùng nguyên, status configured. Auto thử comma, semicolon,
tab, pipe trên tối đa 64 record đầu, theo codec strict và CSV quote/field limit.
Record trống không góp width nhưng vẫn tính vào giới hạn đọc. Candidate phải
có multi-column evidence ở ít nhất nửa record nonempty. Ưu tiên candidate có
width ổn định toàn mẫu; nếu còn nhiều candidate thì csv_delimiter_ambiguous,
yêu cầu cấu hình tường minh. Không có multi-column evidence dùng comma với
single_column_default; candidate duy nhất dùng auto_unique, lưu width/counts.

Đây là policy hữu hạn, không bảo đảm suy đúng mọi CSV. Conflict không bị giải
bằng thứ tự ưu tiên tùy ý. Toàn file vẫn được parse strict sau sampling;
ragged rows được giữ, không drop/fix row. Short/one-column CSV và delimiter
trong dữ liệu có thể không đủ bằng chứng ngữ nghĩa; override là đường lui.
Malformed quotes, limits, undecodable hoặc nguồn thiếu làm business fail-closed;
không silently bỏ file/partial load để trả lời từ dữ liệu thiếu.

## Override theo nguồn

Các flag CSV là cấu hình explicit toàn lượt. Khi cần khác nhau theo file,
dùng `datamate ingest ... --format-map PATH`:

```json
{
  "version": 1,
  "files": [
    {
      "business_id": "tenant_synthetic",
      "source_file": "table.csv",
      "source_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "encoding": "latin-1",
      "delimiter": ";"
    }
  ]
}
```

Ví dụ synthetic; thay SHA bằng hash thật. Encoding/delimiter có thể bỏ qua
để dùng auto. Map phải ngoài raw/cache/output, tối đa 8 MiB; duplicate/unknown
business/file hoặc SHA stale bị từ chối. Override relevant của business nằm
trong fingerprint; hash map ghi trong run report. API:
`LoaderOptions(csv_formats=(CsvFormat(...),))`. Không nhúng override theo BTC
business ID vào code. Source đổi phải xác nhận lại override. Header nhãn
benchmark không đi vào inference runtime.

## Text quality và cache

Profiler quét text CSV/XLSX/SQLite và README: NUL, U+FFFD, C1, non-NFC, literal
`_xHHHH_`, một số mẫu mojibake. Lưu counts và tối đa 5 tọa độ/flag/unit,
không ghi giá trị vào log/index lỗi. Flag có thể false positive, không tự
sửa hoặc kết luận corruption. Chưa có legacy mapping xác minh nên không gọi
đây là detector TCVN3/VNI. Literal OOXML escape được giữ và báo cờ; case thật
cần reader spec và regression riêng trước thay diễn giải chuỗi.

Code/policy/options đổi tạo generation mới. Cache cũ giữ nguyên; DB binary
hash có thể khác vì metadata mới. Acceptance so frame digest từng unit,
row/value/type/provenance và raw hashes; không sửa manifest để reuse stale.
