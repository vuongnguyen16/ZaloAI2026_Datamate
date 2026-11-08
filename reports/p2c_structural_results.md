# P2c: cấu trúc binding, diagnosis theo metric và semantic proposals

Ngày08/11/2026, base664e5d4, nhánh `work/p2c-structural-binding`.
Thuộc P2 đang active, giữ G2/split/scorer. Báo cáo này ghi bằng chứng theo
từng bước; phần chưa đo không được coi là nghiệm thu.

## Scope và triển khai

- CLI `p2_binding_audit.py diagnose`/`diagnose-worker` dùng cùng dev scope và
  verified reader; bảng source/blocker theo từng metric chỉ là hypotheses.
- Binder nối core header–detail: cần header thật đã xác minh; metadata thiếu
  có thể kế thừa, metadata mơ hồ không được coi như thiếu; kiểm duplicate/
  orphan/conflict. Bảng số lượng trả có định nghĩa đóng chuyển quantity>0
  thành event returned theo chính sách core; cả dòng quantity0 phải có đơn.
  Nguồn event có metadata chưa được hỗ trợ vẫn unresolved.
- Bảng quy đổi chỉ loại đối với metric unfiltered khi toàn bộ cột có nghĩa
  quy đổi rõ trong từ điển đóng; không dùng thiếu ngày/khóa hoặc tên file để
  chứng minh loại nguồn. README/header conflict vẫn veto.
- Count không phụ thuộc parse tiền; doanh thu cần net semantics và amount
  đầy đủ. Blocker có thể đồng thời thuộc(a)/(b)/(c); số mẫu lặp đếm business
  distinct và báo cụm riêng, không lấy nhiều sheet thành nhiều business.
- Semantic proposal adapter có source-role/column và status cases, JSON đóng,
  trích dẫn nguyên văn, kiểm cột có thật, unknown khi chưa có căn cứ. Quote
  hợp lệ không chứng minh nghĩa đúng; không tự áp binding/capability.
- Cache key gắn nội dung/code bundle/model revision/rulebook. Kết quả cloud
  phải có đủ case, exit0/cleanup/no timeout, offline/read-only/snapshot và
  sampled/Torch peak<=30GiB trước ghi cache. Output bị reject của run hoàn tất
  cũng lưu là rejected để không tự suy luận lại cùng nội dung.

## Diagnosis và vòng rule đầu

Reconnaissance scoped18dev/212unit:71mẫu header chính xác,18mẫu lặp; các
header unresolved không chứng minh cấu trúc đã hiểu. Artifact chi tiết chỉ
local trong `runs/p2c-structural-20261108/`.

| Mẫu ngữ nghĩa/cấu trúc | Business | Cụm |
|---|---:|---:|
| Bảng dòng có đủ metadata đơn | 8 | 2 |
| Header–detail | 9 | 2 |
| Bảng quy đổi đủ định nghĩa và header đã xác minh | 4 | 1 |
| Bảng số lượng khách trả có định nghĩa rõ | 2 | 1 |

Những nhóm này có thể chồng lấp. Chữ ký header bảng quy đổi xuất hiện5business,
nhưng chỉ4đủ header evidence nên không gọi cả5là mẫu đã xác minh.

Lượt audit đầu `runs/p2c-structural-audit-20261108/` vẫn1/18business qua kiểm
cả count/revenue, thuộc1cụm. Đây là dữ liệu trước các fix review cuối, không
dùng làm record source-current sau khi code đổi. Các blocker không loại trừ:
unknown_status13business, unresolved_source_role12, row-resource guard2;
revenue còn arithmetic_screen_failed4, amount_format_unverified4,
number_scale_ambiguous1 và net_semantics_missing2. Không coi13nhãn chưa map
là13lỗi LLM hoặc suy nghĩa nhãn bằng tần suất.

**Áp dụng điểm dừng:** không thêm khả năng rule sau vòng header–detail/events
vì chưa có cụm thứ hai qua kiểm. Chuyển sang proposal LLM nhỏ; không nới guard
hoặc mở calibration. Lượt audit cuối và CPU gate ghi sau khi source ổn định.

## Review và regression

Review độc lập chỉ source/synthetic, không gửi kit/gold/membership/packet thật.
Ba Important CPU đã tái hiện RED rồi sửa GREEN:

1. Hai cột date/status cùng nghĩa bị rơi khỏi candidate rồi coi như metadata
   thiếu: nay phân biệt ambiguous, không cho kế thừa header để che nhãn lạ.
2. Nhận dạng return_quantity làm mất status/date: nay nguồn mixed metadata
   chưa hỗ trợ phải unresolved, không xóa metadata để qua gate.
3. Duplicate header che blocker ở nguồn sau: nay giữ blocker rồi quét nguồn
   sau trong budget; resource/provenance vẫn terminal, không claim full scan.

Ba Important proposal đã sửa trước cloud: kiểm envelope và đủ case trước
cache; kiểm cache identity/terminal status, đưa cache vào validation output;
hash cả dependency/parser/process/image/runtime lock. Reviewer xác nhận
không còn Important trong scope source/synthetic;40selected tests pass8,75s.
Không thay thế human binding approval, full CPU hoặc model/PA evidence.

Test kill/resume gốc pass một lượt21,20s không sửa code. Lỗi timeout35s ở gate
trước vẫn chưa xác định nguyên nhân; không gọi là đã sửa chỉ vì rerun pass.

## Probe LLM và cổng kiểm

Đã chuẩn bị13case sau gộp nội dung trùng từ tối đa2business/cụm; case nguồn
chỉ schema/header và excerpt README, case trạng thái chỉ một nhãn lấy từ mẫu
tối đa128dòng đầu + rulebook. Không gold/câu hỏi/row samples/membership/path
cache tuyệt đối trong cloud payload. Đây không phải inventory đủ hoặc PA.

User xác nhận credit>=30USD trong phiên; live workspace/user đúng
`vuonghungnguyen07`. Dự toán bảo thủ10USD, ceiling30USD, không hard cap.

Lượt đầu [ap-xWPWXkNx9WRQjrAqD72Ikc](https://modal.com/apps/vuonghungnguyen07/main/ap-xWPWXkNx9WRQjrAqD72Ikc)
fail trước snapshot/model: outer Python import helper diagnostic qua
`model_probe`, kéo pydantic chỉ có trong locked venv vào tiến trình hệ thống.
Artifact lỗi giữ tại `runs/p2c-proposal-model-20261108/`; chưa có model output
và không cache kết quả. Không gọi đó là chưa upload: payload dev tối thiểu đã
được truyền cho function trong phạm vi được cấp, không có gold.

Python-S tái hiện cùng ModuleNotFoundError; tách sanitizer stdlib vào
`probe_diagnostics.py`, giữ API reexport của model_probe, đóng gói helper cho
cả staging/GPU và gắn vào cache fingerprint. Regression GREEN; reviewer
xác nhận77synthetic pass/1skip8,30s. Converter cũng sửa false-negative bằng
kiểm tương thích từng label-role với nghĩa quy đổi đã đăng ký: chú thích
product hợp lệ được nhận, order/date/status/money mâu thuẫn vẫn veto.

Một lượt kiểm chứng revision đã sửa được thực hiện sau gate/preflight/review
mới; SDK retries0. Dự phòng gộp20USD cho hai lượt dưới ceiling30USD, đây không
phải chi phí thực hoặc billing cap. Kết quả thật của lượt này ghi riêng khi
hoàn tất; không dùng phần chuẩn bị làm bằng chứng đã chạy model.

## CPU trước model

`uv run --locked python scripts/check.py` sau fix runtime/converter:549passed,
2skipped trong131,61s, Ruff lint/format pass, source không đổi. Đã đọc gate.json
và ba log; context passed/current, không warning/planning error:
`runs/cpu-check-20261108T033952465812Z-t286r29w/gate.json`.
Gate547passed/2skipped134,81s trước đó là lịch sử trước fix stdlib/converter.
CPU sau cập nhật tracker cuối phiên cần kiểm riêng; CPU không chứng minh GPU
hoặc PA. Không thay timeout/assertion của test kill/resume.

## Kết quả cuối trên source đã sửa

Audit18dev tại `runs/p2c-structural-audit-20261108-v3/` vẫn **1/18business,
1cụm** qua cả hai metric. Không đạt acceptance>=2cụm; chưa PA/G2. Header–detail
và return quantity được nối/kiểm synthetic nhưng business có các nguồn đó
còn blocker khác, không được suy thành capability business.

Blocker không loại trừ: unknown_status13, unresolved_source_role12,
repeated_unresolved_structure6, unresolved_header6, date_format_unverified3,
row-resource guard2. Revenue thêm arithmetic_screen_failed4,
amount_format_unverified4, net_semantics_missing2, number_scale_ambiguous1.
Guard terminal có thể để nguồn sau chưa quét; các số là blocker đã quan sát,
không là inventory nhãn đầy đủ hoặc phép đo semantic accuracy.

Business qua kiểm:22.428đơn/56.501dòng, ledger7,26s, tổng worker12,92s,
peak process146,61MiB. Không phải business lớn nhất toàn dev; không chứng minh
ngân sách6giờ hoặc so tốc độ có kiểm soát với lượt trước.

Lượt model đã sửa [ap-B3NoZEEC0ILIr4tN7dAwrt](https://modal.com/apps/vuonghungnguyen07/main/ap-B3NoZEEC0ILIr4tN7dAwrt)
completed; artifact local `runs/p2c-proposal-model-20261108-v2/`, payload v3.
Qwen3-14B revision40c069824f4251a91eefaf281ebe4c544efd3e18,13case/13lần sinh:

| Quan sát | Kết quả |
|---|---:|
| JSON đúng schema | 12/13 |
| Output qua toàn bộ kiểm, đều chọn unknown | 8/13 |
| Output bị reject | 5/13 |
| Mapping ngữ nghĩa mới được chấp nhận | 0 |
| Prompt token | 211–982 |
| Tổng output token | 955 |
| Engine startup | 29,83s |
| Tổng wall time các request | 96,34s |
| Child wall time, gồm startup | 137,40s |
| Sampled total-device peak | 29,8389GiB |
| Torch allocated/reserved peak | 28,9797 /29,0898GiB |

Exit0, không timeout, process group cleanup pass; snapshot hash verified,
weights read-only và outbound blocked. Runtime Python3.11.18/vLLM0.11.1/
torch2.9.0+cu128/CUDA12.8, sm_120. Imageim-WDiL6DmknIi4dyOH7qE14c; evidence key
a260d2da7d624771917d3e739ad4594c trên Volume dev hiện có. App đã completed,
live container inventory rỗng; không có automatic retry hoặc job còn chạy.
Billing thực chưa đọc được, không ghi0USD.

Năm reject:2duplicate binding column/role,2citation không có trong evidence,
1truncated JSON ở256token. Một case nguồn không có excerpt phù hợp nên thiếu
bằng chứng; không gán mọi reject/unknown thành model không hiểu nghiệp vụ.
Tất cả output, kể cả rejected, được cache theo identity và đưa vào
`review-packet-local.md` cạnh result; không auto-apply hoặc auto-reinfer.
13case này đo proposal transport/format, không là benchmark question-intent,
PA, độ đúng binding, hay throughput toàn1895dev/6giờ.

**Kết luận quyết định:** giữ điểm dừng rule. Probe xác nhận runtime/guard,
nhưng chưa tạo mapping mới dùng được. Bước kế tiếp trong P2 là kiểm completeness
của projection/citation và giao thức role-only cho nguồn ngoài ledger bằng
synthetic/dev evidence, cùng duyệt ngữ nghĩa nhãn chưa rõ. Chưa đủ căn cứ để
nối các output này vào predict hoặc chạy toàn dev. Short-intent/throughput
vẫn cần probe riêng sau khi có binding được duyệt ở cụm thứ hai.

Case status dùng rulebook nguyên vẹn nếu<=8.000byte, nếu dài hơn chỉ dùng
prefix liên tục2.500ký tự. Projection hiện chưa chọn đúng điều khoản cho từng
nhãn và chưa có omission flag trong prompt; đây là giới hạn input của probe,
cần kiểm trước khi kết luận về năng lực model hoặc mở rộng job.

## Xác minh cuối phiên

Sau cập nhật backlog/state/evidence: full locked CPU gate **549passed,
2skipped131,01s**, Ruff lint/format pass, source không đổi, exit0:
`runs/cpu-check-20261108T035243599907Z-2fxo7vwy/gate.json`.
Timeline DOCX/web/asset/tracker current;27tệp thay đổi UTF-8/NFC pass.
Graphify AST đã cập nhật1199node/4062edge, không index data/gold/runs/docs.
Theo yêu cầu08/11, nhánh `work/p2c-structural-binding` được chuẩn bị xuất bản
để review source/synthetic và báo cáo tổng hợp; chưa merge. Gold/split/raw/
cache cũ và mọi packet/payload BTC giữ local; không chạy PA hoặc P3. Cổng CPU
được kiểm lại trước commit; CI GitHub của head xuất bản kiểm riêng.

Gate trước xuất bản08/11:549passed/2skipped131,45s, Ruff lint/format pass,
source không đổi, exit0; `runs/cpu-check-20261108T041210308529Z-ervunqx1/gate.json`.
Đã đọc JSON/ba stage log và đối chiếu context current trước commit.
