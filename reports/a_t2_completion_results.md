# Hoàn thiện A-T2 — runtime format, header/data-start và descriptor

Ngày 05/11/2026. Người dùng giao hoàn thiện sau phản biện Claude; thay phạm
vi chỉ engineering trước đó bằng kiểm chứng header CPU có giới hạn. Nguồn
kế hoạch/giới hạn: [spec trước implementation](../docs/research/a_t2_completion.md),
timeline DOCX A/T2 và contract repo. Review bởi tác giả; không reviewer thứ hai.

## Thay đổi và ranh giới

- Codec runtime BOM UTF-8/UTF-16 hoặc strict UTF-8 khi không BOM; status rõ,
  không fallback 8-bit. Delimiter candidate hữu hạn có conflict/error path.
  Global explicit config và format-map theo file gắn source SHA có cache
  fingerprint, validation, source-change và malformed input tests.
- README cùng codec policy; text QA trên CSV/XLSX/SQLite/README chỉ đếm/cờ/
  tọa độ. Không sửa mojibake/NFC, không converter legacy. Mapping legacy chưa
  có nguồn/mẫu thật nên hoãn, không dựng detector phức tạp khi chưa cần.
- Header rule `header-conservative-1` đọc raw prefix đầy đủ theo budget,
  dense labels + generic anchors + value-shape change; có abstention cho
  nhiều candidate, header lặp, toàn text/không đủ evidence và byte limit.
  Sparse group header liền trước được giữ. Không đọc ID, README dictionary,
  nhãn survey/benchmark hoặc oracle annotation để dự đoán runtime.
- Descriptor có header rows, physical data-start, header_cells, data_samples
  riêng, bounded preview khi unresolved và format/text flags. Giữ tên SQL
  positional; label/value không là lệnh/SQL alias. Không đổi raw view/schema,
  không bỏ header/totals/notes, fill nhóm, dedup hoặc normalize tiền/ngày.

Hướng dẫn: [runtime format](../docs/runtime_format.md),
[profiling](../docs/profiling.md), [ingestion](../docs/ingestion.md).
Code mới ở `ingest/text_format.py`, `profile/structure.py`,
`profile/text_quality.py`; tích hợp vào loader/profiler/CLI và hai auditor.

## Nhãn và nghiên cứu header có giới hạn

Khảo sát cũ chỉ có một header_row. Đối chiếu prefix nguồn và README trước
viết/chọn rule phát hiện **34 unit có header hai tầng**, cần giữ cả group row
và leaf row; title/metadata phía trên không phải tầng header. Tập nhãn 322
CSV/sheet dùng tọa độ vật lý và first data row, 0 nhãn ambiguous theo protocol.
261 unit có leaf header khớp exact multiset README; phần còn lại kiểm source/
README dạng sheet/partial cùng survey lịch sử. Đây là README corroboration
và same-author source review, không giả là human-label độc lập.

Đóng băng labels trước đo: SHA-256
`3eb90b23bf13b185559a4d1a87f7c6a932044d0e654b2410c3e66d24d8815ef6`.
Canonical header grids tạo 95 templates, hợp nhóm file hash trùng thành 80
components. Hash split cố định cho 52 nhóm/103 unit dev và 28 nhóm/219 unit
check. Tỷ lệ theo unit không 60/40 vì kích thước nhóm khác nhau; không đổi seed
để làm đẹp metric. Toàn train đã từng khảo sát: đây là structural check, không
unseen QA holdout và không thay E-SPLIT. Không gold/public/private được dùng.

| Phương án | Partition | Auto / unit | Chọn sai | Macro group coverage |
|---|---|---:|---:|---:|
| B0: hàng đầu | dev | 103/103 | 38 | 100% |
| B1: dense text/lookahead | dev | 99/103 | 0 | 94,10% |
| B2: thêm anchor/value-shape | dev | 93/103 | 0 | 88,08% |
| B0 | check | 219/219 | 77 | 100% |
| B1 | check | 218/219 | 0 | 96,43% |
| B2, chọn trước check | check | 218/219 | 0 | 96,43% |

B2 được chọn trước check vì từ chối các ca synthetic toàn text/headerless/
header lặp mà B1 có thể chọn nhầm; chấp nhận coverage dev thấp hơn. Toàn train
B2 chọn 311/322 unit (96,58%), 11 unresolved, không auto-selection sai theo
bộ nhãn. Exact header-row set và data-start đều khớp trên các unit được chọn.
0 lỗi quan sát không chứng minh 0 lỗi private; mẫu không IID, labels chỉ có
same-author review. Không tune lại theo lỗi/coverage check hoặc thêm ngoại lệ ID.

Nhãn, evidence, partition và từng prediction giữ local/ignored tại
`runs/a-t2-completion-20261105/`: `prefix_evidence.json`, `labels_frozen.json`,
`labels_freeze.json`, `rule_selection.json`, `header-dev-final.json`,
`header-check-final.json`. Script prepare/freeze/benchmark cùng thư mục lưu
đủ phép tái hiện. Benchmark không phải B0 model baseline của dự án; B0 ở bảng
trên chỉ là tên phương án header đơn giản.

## Kiểm chứng dữ liệu và CPU

Cold ingest mới exit 0, 30/30 business, 339 unit, 3.997.599 rows và
3.997.518 nonempty, 766,60s trong lượt đo local có các việc CPU khác. Toàn bộ
339 frame digests trùng A-T1 trước thay policy; hash raw 162 file và cache cũ
60 file không đổi. Metadata/code/options tạo generation mới, không giả rằng
DB binary phải giống generation cũ. Evidence: `ingest_acceptance.json`.

Source auditor riêng đạt 339/339 unit, so toàn giá trị/type/position và README
decode theo codec đã resolve; exit 0, 359,70s. Artifact:
`runs/a-t2-completion-20261105/source-audit/verification.json`. Auditor không
gọi production readers, gold chỉ hash nhị phân. Việc sửa QA README phía sau
không đổi loader/auditor/cache; các hash này được kiểm lại trong final proof.

Cổng CPU mới sau fix cuối: exit 0, Ruff/format pass, **144 tests** trong
44,83s, không skip; source không đổi trong gate. Artifact:
`runs/cpu-check-20261105T081753167962Z-qao9tpkg/gate.json`. Đã đọc JSON/log;
source fingerprint và final profile proof sẽ được đối chiếu khi bàn giao.

Final profile proof `runs/a-t2-completion-20261105/final_acceptance.json` đã
đạt valid=true, source/raw/cache unchanged và 60 business profile/schema
hashes giống hệt qua hai lượt source hiện hành. Source fingerprint
`c8f3b52a611dd0ec042835aa2bcc7b9321814551cb130cffe78f5a455f994337`
trùng CPU gate sau fix NEL. Đã đọc final JSON/log và profile audit JSON.

| Lượt hiện hành | Kết quả/thời gian |
|---|---|
| Warm cache | 30/30 hits; 3,94s |
| Profile final first | 30/30 business, 339 units, 3.184 columns, 3.997.599 rows, 33.628.129 present cells; 241,61s |
| Profile final repeat | Cùng counts và 60 hashes; 302,13s |
| Independent profile auditor | 339/339 units, 3.184 columns; stats/types/extrema/sample/header provenance và descriptor match; 219,74s |
| Structure runtime full train | 311 auto_rule, 11 unresolved, 17 source_schema; 0 sai trên nhãn đã đóng băng |
| CSV runtime | 20/20 bom_utf_8 + delimiter auto_unique, không override train |
| Text/README QA | Không ghi nhận cờ trong lượt quét, không sửa bất kỳ giá trị nào |

Không ghi nhận cờ không chứng minh mọi cách mã hóa legacy đều vắng mặt:
converter/font mapping chưa có evidence và scanner chỉ có những phép kiểm
đã mô tả. Lượt `acceptance.json` trước fix NEL được giữ riêng, source guard
đã báo stale/invalid khi source thay; không dùng nó để kết luận phiên bản
cuối pass. Raw/source-auditor code không đổi qua fix này, được final proof
kiểm hash để kế thừa đúng evidence source audit. Thời gian là wall time local
có biến động tài nguyên, không là phép so sánh throughput có control.

29 regression mới trong `tests/integration/test_t2_completion.py`, giữ nguyên
các regression nền/raw/statistics. Kiểm BOM LE/BE, strict UTF-8, short/ASCII,
cp1258 bytes từ chối, BOM conflict, delimiter ambiguity/quoted decimal,
file-specific override/cache/stale hash, UTF-16 README/undecodable location,
physical row gaps, two-tier/duplicate header, numeric/all-text/headerless/
repeated-label abstention, rộng 40 cột, injection label, data-start consumer
SQL và data_samples, evidence budget, text flags và README C1/NEL.

Các lỗi trung gian giữ trong evidence: tuple options chưa canonical JSON làm
cache integrity fail (đã sửa serialization, không bỏ integrity checks);
header lặp khiến rule chọn lần lặp phía sau (thêm abstention, regression);
README decode error thiếu file location (tái hiện rồi sửa); splitlines loại
NEL trước QA khiến mất cờ C1 (tái hiện, đổi sang physical LF và thêm test).
Lượt pipeline trước fix cuối không dùng làm bằng chứng source hiện hành;
final profile/audit phải được chạy lại, cache raw giữ nguyên hợp lệ.

## Acceptance, giới hạn và handoff

A-T2 sở hữu format/profile/structure/descriptor/consumer contract. Theo yêu
cầu hoàn thiện và phản biện, yêu cầu actual schema-in-prompt/PA được giữ rõ
ở D-E-T2, thêm dependency A-T2. Không xóa milestone tích hợp hoặc dùng CPU
test thay cho model/scorer. A/B oracle/detector/preview và lựa chọn prompt
representation chỉ làm khi D/E/model/split sẵn sàng.

Data-start là cận dưới, không phải chứng nhận mọi hàng sau đó là giao dịch.
Một bảng toàn text, numeric header, nhiều candidate hoặc ngoài budget có
thể unresolved. Có thể có false negative/false positive ngoài các family đã
đo; preview và status giữ thông tin để consumer không bị ép tự tin.
Codec/delimiter hợp lệ cũng không bảo đảm ngữ nghĩa văn bản đúng; QA flags là
heuristic, không là sửa lỗi hoặc bảo đảm sạch. UTF-32 BOM, legacy conversion,
multi-region và SQLite invalid-TEXT fallback chưa có hỗ trợ mới.

DuckDB 2 threads/256 MB; không phải hard RSS cap Python hoặc model SQL sandbox.
Không mở cloud/model, scorer, tuning, Docker hoặc A-T3 cleaning trong phiên.
Không sửa data/kit manifest, không commit/push/upload; profile/nhãn/raw giữ local.

A-T2 đã đóng ở phạm vi trên sau yêu cầu hoàn thiện của người dùng; actual
model/prompt/PA milestone vẫn mở ở D-E-T2, không báo nó đã đạt. Source mới
chưa publish lên GitHub trong phiên này.

Handoff cuối tại `runs/a-t2-completion-20261105/handoff_verification.json`:
final proof/frozen label/rule hashes còn current, A-T2 done, CPU passed/current,
không warning. D-E-T2 vẫn todo/blocked bởi các prerequisite còn thiếu. Kit
train/public/thể lệ và cache cũ không đổi (public chỉ hash nhị phân); protected
config/lock/contract manifests/Docker không đổi. 12 tài liệu/tracker UTF-8/
NFC/JSON và 53 link local hợp lệ, diff/format pass. Nhãn/profile/raw tiếp tục
được gitignore; không publish dữ liệu hoặc coi QA flags là proof sạch tuyệt đối.
