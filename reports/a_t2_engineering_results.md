# A-T2 — Nghiệm thu phần engineering của profile raw

Ngày 05/11/2026. Người dùng giao **chỉ engineering**, hoãn research. Nguồn kế
hoạch vẫn là timeline DOCX A/T2 hiện hành, hash
e74b1292119f01ca3eae7d20d709921219efc30e655e01909685c50d5363eb51.
Review bởi tác giả (self-review); auditor riêng kiểm thống kê bằng cách khác,
không phải review bởi người/agent thứ hai.

## Phần đã triển khai

| Nội dung | Implementation |
|---|---|
| Profile bảng/cột | Quét đầy đủ raw rows, physical types, width/counts, missing/NULL/empty/nonempty và ratios |
| Mẫu và min–max | Mẫu nonempty distinct đầu tiên có tọa độ; lexical/length extrema toàn cột; numeric extrema chỉ từ kiểu numeric vật lý, không qua float |
| Header/encoding engineering | Header SQLite từ declared schema; CSV/XLSX unresolved + row preview; annotation nhiều tầng explicit gắn fingerprint; codec/delimiter từ manifest |
| Giao diện cho baseline | Schema JSON có tên view/cột SQL thật, SQL type, physical type counts, sample/label evidence; consumer synthetic truy vấn được dữ liệu |
| Bảo toàn và lỗi | Cache readonly; kiểm source/cache/catalog/frame digest; staging/atomic publish; lỗi theo business, limits, không log cell value |

Code: `src/datamate/profile/`, CLI `datamate profile`, auditor
`scripts/verify_profile.py`, 28 test profile mới. Không sửa module ingest,
dependency/lock, contract semantics hoặc Docker. Quyết định trước implementation:
[spec engineering](../docs/research/a_t2_engineering.md). Cách chạy/API/định nghĩa
thống kê và giới hạn: [hướng dẫn profile](../docs/profiling.md).

## Kiểm chứng toàn train

Artifact local/ignored: `runs/a-t2-engineering-20261105/`. Dùng nguyên generation
30 DuckDB đã nghiệm thu A-T1; input ingest report:
`runs/a-t1-loader-acceptance-20261105T050128Z-j5zoovbj/final-warm/ingest.json`.

Lượt profile đầu: exit 0, **151,99 giây**, 30/30 business thành công,
339 unit, 3.184 cột, 3.997.599 hàng raw và 33.628.129 cell có mặt. Đây là toàn
hàng vật lý kể cả header/tổng/ghi chú/trùng/trống, không phải số giao dịch.

322 CSV/XLSX units giữ header unresolved; 17 bảng SQLite dùng schema khai báo.
Không tạo annotation header riêng cho business BTC hoặc nhập quyết định header
từ khảo sát vào code. Toàn train có thể truy cập qua schema raw positional;
chưa đồng nghĩa schema nghiệp vụ đúng hoặc baseline/prompt chất lượng tốt.

Các lệnh đã chạy qua `.tools/uv/uv.exe run --locked`:

```powershell
datamate profile --input data/train --ingest-report INGEST/ingest.json --output RUN/profile-first
datamate profile --input data/train --ingest-report INGEST/ingest.json --output RUN/profile-repeat
python scripts/verify_profile.py --input data/train --report RUN/profile-first/profile.json --output RUN/audit
```

`RUN`/`INGEST` tương ứng các đường dẫn local ở trên; `acceptance.json` ghi đầy
đủ argv, exit code, thời gian, source/raw/cache hashes và tính tất định.
Lượt lặp đạt exit 0 trong **152,62 giây**, đủ cùng counts. Cả 30 profile và
30 schema JSON có SHA-256 giống hệt lượt đầu với cùng input/config/code.
Auditor riêng đạt exit 0 trong **153,29 giây** (152,27s phần audit nội bộ):
30 business, 339 unit, 3.184 cột và 3.997.599 hàng đều match. SQL GROUP BY
kiểm counts/types/length/lexical extrema; pass riêng kiểm numeric extrema
vật lý, tọa độ mẫu và DESCRIBE đối chiếu schema thật. Không gọi code profile/
stats production; không khẳng định mẫu đại diện hoặc header đã đúng.

`acceptance.json` có `valid=true`, `deterministic_business_outputs=true`,
`raw_unchanged=true`, `cache_unchanged=true`, `source_unchanged=true`. Đã đọc
JSON và log cả ba stage, cùng `audit/verification.json`. Hash 162 file train
và 60 file cache (30 database + 30 manifest) trước/sau không đổi; không parse
gold. Source fingerprint trùng cổng CPU hiện hành bên dưới. Thời gian là một
lần đo local, không phải benchmark model hoặc cam kết runtime triển khai.

## CPU và regression

`uv run --locked python scripts/check.py`: exit 0; Ruff check/format pass;
**115 tests passed trong 27,51 giây**, không skip. Đã đọc gate.json và cả ba
stage log tại `runs/cpu-check-20261105T062508275441Z-5p01bmls/`.
Source không đổi trong gate; fingerprint
`da548568cc12ebedad7b23f3e4c07b0ce7f8c24a548db20f5863032d8b8847da`.
28 test profile riêng đạt trong 14,76 giây trước cổng đầy đủ.

Handoff xác nhận context A-T2 in_progress/engineering done/research deferred,
CPU passed/current, không warning. Kiểm kit theo manifest: hash train/public/
thể lệ không đổi (public chỉ hash nhị phân). Code ingest trùng generation
A-T1; lock/config/contract manifests và Docker không đổi. Kiểm 7 tài liệu/
tracker UTF-8/NFC/JSON, 36 liên kết local, diff/format đều pass. Evidence:
`runs/a-t2-engineering-20261105/handoff_verification.json`.

Các test có giá trị kỳ vọng từ fixture synthetic cho cả CSV/OOXML/SQLite:
leading zero, số nguyên int64, finite/nonfinite/invalid/too-long numeric,
serial không đổi thành ngày, BLOB/NULL/rỗng, sparse/missing, formula không cache,
unit không hàng/cột, Unicode byte truncation/hash, determinism và consumer SQL.
Header nhiều tầng/trùng/missing giữ nguyên evidence; stale/unknown/duplicate/
absent/unsorted/bool row annotations bị từ chối. Có round-trip codec explicit,
kiểm lỗi source/cache/manifest/report, source đổi lúc quét hoặc staging và sáu resource
limits. Business fail không có profile/schema hoàn chỉnh, business khác tiếp
tục. Gold guard xác nhận profiler không mở gold.

Auditor synthetic được kiểm cả pass và tình huống sửa sai thống kê rồi cập
nhật hash artifact: SQL aggregate vẫn phát hiện mismatch. Các lỗi trung gian
được xử lý có nguyên nhân: fixture ban đầu cộng nhầm present cells (thực tế
CSV 11 + OOXML 7 + SQLite 12 = 30) và test mới thiếu import LoaderOptions;
đã sửa fixture/import, không thay định nghĩa thống kê hoặc bỏ test.

## Phần hoãn và trạng thái task

**Engineering A-T2** gồm profile raw/descriptor/explicit metadata và failure
paths. **Chưa làm research**: tự dò TCVN3/VNI/mojibake/encoding, tự chọn header
thật/table region, semantic column inference và chiến lược biểu diễn cho LLM.
Không đồng nhất codec cấu hình với encoding đã được phát hiện đúng, hoặc
annotation với header được xác nhận đúng. Chưa prompt baseline/model/PA.

Không normalize tiền/ngày/sentinel, fill nhóm, dedup, bỏ tổng/header, gộp bảng,
join/entity discovery, tuning hoặc thiết kế split trong increment này. Min–max
numeric chỉ thuộc cell có type numeric vật lý; CSV/text không bị ép kiểu.
Sample không được coi là đại diện và preview không phải giá trị đầy đủ.

Giới hạn: budget DuckDB 2 threads/256 MB không phải hard RSS cap Python;
extrema giữ lại có budget 16 MiB/unit, output 64 MiB/file/business. Vượt limit
báo lỗi thay vì giảm coverage. Không có profile cache/resume hoặc SQL sandbox
cho model. Sự bất biến toàn lượt được kiểm bằng hash trước/sau, không khóa
toàn split thành transaction chung. Profile chứa cell samples chỉ lưu local.

A-T2 giữ **in_progress** vì acceptance detection/header và dùng trong prompt
baseline thực tế còn lại; research **deferred_by_user**. Không tự công nhận
toàn A-T2 hoàn tất hoặc mở A-T3/T4. Không cloud/model, PA, commit/push/upload.
