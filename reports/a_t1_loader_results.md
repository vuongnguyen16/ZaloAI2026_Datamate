# Nghiệm thu A-T1 — loader raw và cache theo business

> Bằng chứng module được giữ từ các phiên A-T1/A-T2 trước migration. Tham chiếu tuần, hash kế hoạch và handoff bên dưới là lịch sử; kế hoạch hiện hành là P0–P9 trong [state](../docs/project_state.md) và [backlog](../tasks/backlog.json).

Ngày 05/11/2026. Phạm vi: hoàn tất A/T1 của timeline DOCX hiện hành, tiếp nối
khảo sát train đã lưu. Implementation và dữ liệu được kiểm tra local; chưa
commit/push hoặc upload kit. Review do tác giả thực hiện (self-review).

## Kết quả và acceptance

| Acceptance A-T1 | Bằng chứng |
|---|---|
| Khảo sát định dạng/dòng/cột/README | [Khảo sát sâu](../docs/research/a_t1_deep_survey.md) và các artifact local; note sơ bộ đã lưu trong [archive](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/tree/archive/timeline-20261103) |
| Mọi business nạp được, có lỗi cấu trúc | Full train 30/30 business thành công; fixture kiểm lỗi CSV/XML/ZIP/SQLite/limits và cô lập business lỗi |
| Giữ raw, fingerprint/cache theo business | Đối chiếu đầy đủ nguồn–cache, read-back frame digest, 162 hash raw bất biến; warm run 30/30 cache hits; regression invalidation/corruption/atomic build |

Loader tại [src/datamate/ingest](../src/datamate/ingest/__init__.py), CLI
`datamate ingest`; hướng dẫn và schema ở [docs/ingestion.md](../docs/ingestion.md).
[Spec và quyết định kỹ thuật](../docs/research/a_t1_raw_loader.md) được ghi
trước implementation; không thêm dependency hoặc thay lock/contract.

## Đo trên toàn train

Artifact local, ignored:
`runs/a-t1-loader-acceptance-20261105T050128Z-j5zoovbj/`.

| Chỉ số | Kết quả |
|---|---:|
| Business thành công | 30/30 |
| File bảng | 128: 107 XLSX, 20 CSV, 1 SQLite |
| Đơn vị nguồn | 339: 302 worksheet, 20 CSV, 17 bảng SQLite |
| Hàng raw vật lý | 3.997.599 |
| Hàng có ít nhất một giá trị khác NULL/rỗng | 3.997.518 |
| Hàng trống được giữ thêm | 81 hàng hiện diện rõ trong XML |
| File raw được hash trước/sau | 162, không đổi |
| Tổng kích thước 30 DuckDB | 312.320.000 bytes |
| Cold build, gồm kiểm cache trước publish | 374,85 giây |
| Warm validation/cache reuse | 3,50 giây; 30/30 hits |
| Đối chiếu nguồn độc lập | 243,90 giây; 339/339 unit khớp |
| Warm lần cuối sau bổ sung regression auditor | 3,67 giây; 30/30 hits |
| Đối chiếu toàn nguồn lần cuối | 241,32 giây; 339/339 unit khớp |

Thời gian là một lần đo trên máy local, gồm startup CLI; không phải benchmark
GPU hoặc cam kết throughput. Cache key và runtime được lưu trong từng manifest.
Các số hàng gồm header, lời dẫn, tổng, ghi chú, dòng trùng và hàng trống;
không phải số đơn/giao dịch. Khác biệt với khảo sát 3.997.518 hàng là 81 hàng
trống vật lý, không phải mất/thêm bản ghi nghiệp vụ.

Các lệnh đã chạy qua `.tools/uv/uv.exe run --locked`:

```powershell
datamate ingest --input data/train --cache RUN/cache --output RUN/cold
datamate ingest --input data/train --cache RUN/cache --output RUN/warm
python scripts/verify_ingest.py --input data/train --report RUN/cold/ingest.json --output RUN/audit
```

`RUN` là thư mục artifact ở trên; `acceptance.json` ghi argv tuyệt đối, exit
code, thời gian, source fingerprint và hash raw trước/sau. `cold/ingest.json`,
`warm/ingest.json`, `audit/verification.json` cùng các log đều đã được đọc.
Acceptance ban đầu: `valid=true`, raw/source không đổi trong lượt chạy.

Auditor không gọi production readers: đọc riêng CSV/OOXML/SQLite rồi so mọi
row ordinal/tọa độ, width, cell value, physical type, counts và unit coverage.
Digest được lưu theo unit; lỗi không đưa cell value vào report. Production
loader còn so digest cả payload metadata trước/sau ghi DB. Formula, style,
shared string, epoch, merge, hidden sheet và NULL/empty/missing có fixture
synthetic đối chiếu riêng. Không khẳng định cache thay thế đầy đủ định dạng
Excel; file nguồn và SHA-256 vẫn là bản raw gốc.

## Regression và cổng CPU

`uv run --locked python scripts/check.py`: **exit 0**, Ruff check/format pass,
**87 tests passed trong 15,77 giây**, không skip. Đã đọc gate JSON và cả ba
stage log tại `runs/cpu-check-20261105T051420112942Z-h48l958o/`.
`source_changed_during_gate=false`; source fingerprint:
`1980a674cc985b88560a1c67a9ab907289069e41822e8e68cee335a4c39d59ce`.

28 test ingest bổ sung kiểm round-trip cả ba định dạng; BOM/Unicode/quotes/
multiline/NUL/leading zero; header trùng và ragged rows; sparse/blank cells;
formula có/thiếu cached value; SQLite int64/REAL/TEXT/BLOB/NULL/bảng rỗng;
cache hit không reparse, invalidation theo README/table/config/code, cache
corruption, lock, nguồn đổi giữa build, path alias/junction và output overlap.
Lỗi nguồn/giới hạn không được publish cache complete hoặc rò cell value.

Rà soát cuối phát hiện auditor còn dùng giới hạn trường CSV mặc định của
Python. Đã đồng bộ theo options trong manifest, thêm regression trường dài
150.000 ký tự và kiểm parser limit được khôi phục. Loader không đổi sau cold
build. Lệnh test riêng `python -m pytest ...` đạt 28/28 trong 7,45 giây.

Sau sửa auditor, đã chạy lại warm CLI và đối chiếu toàn train với phiên bản
cuối; `final_acceptance.json` ghi `valid=true`, source/raw không đổi,
`final-audit/verification.json` có 339 unit match. Fingerprint source trùng
cổng CPU hiện hành ở trên. Hash code riêng của loader vẫn trùng toàn bộ 30
manifest cold nên dùng lại generation hợp lệ; không lấy record stale để
chứng minh phiên bản auditor cuối. Chi tiết argv, thời gian, log và hash được
lưu cùng thư mục artifact.

Handoff cuối: context A-T1=`done`, A-T2=`todo`/dependency ready, CPU
passed/current, không warning. Kit audit đối chiếu manifest xác nhận hash
train/public/thể lệ không đổi (public chỉ hash nhị phân). Kiểm 8 tài liệu/
tracker UTF-8/NFC và 32 liên kết local hợp lệ; `git diff --check` và format
cuối pass. Bằng chứng: `handoff_verification.json` cùng thư mục run.

Các lần kiểm tra trung gian được giữ nguyên trong artifact: một lượt gọi
`pytest` trực tiếp lỗi import namespace `scripts`; chuyển sang `python -m
pytest` như cổng chuẩn. Một lượt gate dừng vì format code block trong tài
liệu mới; đã format và chạy lại toàn cổng thành công, không bỏ test/đổi expected.

## Giới hạn và bước tiếp theo

- Lớp raw giữ cột theo vị trí và metadata; chưa chọn header, chuẩn hóa số/ngày,
  fill nhóm, mapping status, dedup hoặc hợp nhất grain. Không biến các giả
  thuyết từ khảo sát thành contract nghiệp vụ.
- SQLite view/virtual/generated column và snapshot có WAL/journal bị từ chối
  rõ; nguồn lỗi/không hỗ trợ không bị bỏ qua. OOXML hỗ trợ transitional/strict;
  không tính formula hoặc truy cập external link.
- Hash cache phát hiện corruption; không xác thực chống người sửa cả DB và
  manifest. Lock bị bỏ lại sau crash cần kiểm tra thủ công. Giới hạn DuckDB
  2 threads/256 MB không phải hard RSS cap toàn Python hoặc SQL sandbox.
- Loader không mở questions/gold/rulebook; auditor chỉ hash nhị phân gold để
  kiểm bất biến, không parse nội dung. Không dùng public/private cho tuning.
  Mức truy cập khảo sát toàn train phải được ghi nhận khi thiết kế split.

**CPU:** passed. **Modal/model:** không chạy. **PA/B0:** chưa đánh giá.
Không tải weights, thay dependency, chạy Docker hoặc cloud job trong increment.

Bước tiếp theo của nhóm A là **A-T2 — profile schema, encoding và header**:
tạo profile bảng/cột/type/sample/null/min–max cùng bản đồ vùng header có nguồn
gốc, phục vụ baseline. Chủ yếu là engineering trên khảo sát đã có; chỉ mở
research hẹp khi cần quyết định cụ thể về header/encoding/type ambiguity.
A-T2 và cleaner A-T3/T4 vẫn chưa được nghiệm thu trong phiên này.
