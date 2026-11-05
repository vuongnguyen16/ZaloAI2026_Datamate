# A-T1 — Khảo sát sâu train

> Bằng chứng module được giữ từ các phiên A-T1/A-T2 trước migration. Tham chiếu tuần, hash kế hoạch và handoff bên dưới là lịch sử; kế hoạch hiện hành là P0–P9 trong [state](../project_state.md) và [backlog](../../tasks/backlog.json).

Ghi chép lịch sử trước implementation. A-T1 hiện đã hoàn tất;
[loader](../../reports/a_t1_loader_results.md) và
[hoàn thiện A-T2](../../reports/a_t2_completion_results.md) có nghiệm thu riêng.
Các giả thuyết nghiên cứu ở đây không tự trở thành contract của hai module đó.

Phạm vi mở rộng theo yêu cầu người dùng ngày 05/11/2026: giải quyết các điểm
chưa rõ của khảo sát đầu vào, trước khi triển khai loader. Đây là research
trên dữ liệu local; không thay contract, không làm sạch raw hoặc xây inference.

Nguồn: timeline DOCX hiện hành mục A/T1–T4 (các công việc sau T1 chỉ được
khảo sát để hiểu dữ liệu, chưa nghiệm thu module), docs/requirements.md,
manifests/competition_contract.json, rulebook và README của train. Kế thừa
bằng chứng sơ bộ tại [archive GitHub](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/blob/archive/timeline-20261103/docs/research/a_t1_train_survey.md). Không parse gold, không
đọc nội dung public/private, không tuning/huấn luyện hoặc gọi cloud/model.

## Câu hỏi cần giải đáp và phép kiểm chứng

1. Header thật nằm đâu; có header lặp, lời dẫn, dòng tổng hay sheet khác schema?
   So metadata/readme với các hàng đầu, rồi quét toàn bộ và lưu tọa độ mẫu.
2. Null là ô thật sự thiếu, cột rỗng, ô kế thừa nhóm hay sentinel? Đếm theo cột,
   đối chiếu vị trí quanh khóa đơn; không tự forward-fill dữ liệu nguồn.
3. Các cách ghi số/ngày cụ thể và tỷ lệ là gì? Thống kê toàn cột, đọc hệ ngày
   workbook/style, ghi riêng mơ hồ/lỗi. Parser khảo sát là giả thuyết có nguồn,
   không phải contract cleaning hay bằng chứng đáp án đúng.
4. Dòng trùng thuộc loại nào? Phân biệt keyed/unkeyed, trùng toàn dòng, khóa
   trùng nhưng nội dung khác, và lặp giữa partition; giữ cả bằng chứng vị trí.
5. Các phép nối nào có bằng chứng? Đo tính duy nhất, inclusion/orphan và fanout
   của khóa do README/schema gợi ý, xét khóa composite; không kết luận chỉ dựa
   tên cột giống nhau hoặc xóa bản ghi để ép khớp.
6. Coverage thời gian của từng nguồn có khớp README và tên sheet không? Đo
   min/max, số ngày và khoảng trống; không đồng nhất không giao dịch với mất dữ
   liệu. Ngày không năm cần năm sheet; phân biệt ngày bán, thu tiền và hạn dùng.
7. Rulebook/README có mâu thuẫn dữ liệu hoặc còn thông tin không thể suy ra?
   Lập sổ điểm đã xác nhận, giả thuyết và câu hỏi còn mở, có mức ảnh hưởng.

Chi tiết chứa raw value chỉ lưu trong runs/a-t1-deep-survey-20261105/ bị Git
ignore. Local dùng các pass streaming, tối đa hai tiến trình CPU độc lập đồng
thời, không thêm dependency. Phiên này không dùng DuckDB. Hash train trước/sau.

## Kết quả đã kiểm chứng

Đã hoàn tất khảo sát sâu trong phạm vi đầu vào train. Artifact chỉ giữ local:
`runs/a-t1-deep-survey-20261105/report.md`, `metrics.json`, `catalog.md`,
30 hồ sơ trong `businesses/`, các pass và bằng chứng JSON kèm script tái hiện.
Không có code inference/loader/cleaner production mới.

- Quét đủ 339 sheet/bảng, 3.184 cột theo sheet, 112 bộ tên cột. Header của
  322 CSV/sheet ở dòng 1/2/3/4 lần lượt 207/34/42/39; SQLite có 17 schema.
- Phân vùng 3.997.518 dòng có nội dung thành 3.994.970 dòng ứng viên nghiệp vụ,
  322 header, 154 lời dẫn, 2.026 dòng tổng theo mẫu và 46 ghi chú. Có 81 hàng
  XML trống tính riêng. Dòng ứng viên chưa dedup và gồm nhiều loại bảng.
- Sau loại ghi chú, 477 cột có ô trống; 216 hoàn toàn trống; 1.076.613 ô trống
  vật lý trước kế thừa nhóm. Không đồng nhất null vật lý với thiếu nghiệp vụ.
- biz_103/121/122 có 114.863 dòng cần thông tin nhóm; diễn giải 459.452 ô
  mã đơn/ngày/trạng thái/khách trong view riêng; không có nhóm mồ côi. Các
  lượt ô thô lặp ở ba nguồn đó không còn lặp toàn dòng khi có ngữ cảnh.
- Sales có 133.987 lượt lặp ô thô khi xét partition theo business; còn 14.271
  lượt keyed lặp sau ngữ cảnh. 16.754 lượt unkeyed ở biz_107/113/126 phải giữ
  theo rulebook. Không phát hiện keyed lặp giữa file/sheet sau ngữ cảnh.
- Kiểm tra 110 quan hệ khóa có nguồn gợi ý: không orphan trên khóa không rỗng.
  Phần lớn kiểm tra parent là mã duy nhất; các kiểm tra sales làm parent chỉ
  chứng minh tồn tại, không chứng minh join 1:1. SQLite không khai báo PK/FK.
  Join sales với receipts làm nhân dòng; biz_109: 80.450 → 92.984 dòng.
- Mã dùng lại giữa business: 78.847 mã đơn xuất hiện ở nhiều business; không
  dùng mã đơn/sản phẩm/khách làm khóa toàn train mà thiếu business namespace.
- 30/30 ngày cuối bán/đặt quan sát khớp README. Mỗi ngày trong khoảng min–max
  đều có bản ghi, không lệch tháng sheet hoặc sự kiện nghiệp vụ sau ngày cuối
  README trong các trường đã xét. Điều đó không chứng minh transaction complete.
- 8.577 ô ngày thiếu năm dùng năm sheet. Workbook dùng hệ ngày 1900. Không
  còn ô ngày không nhận diện sau loại ghi chú, theo giả thuyết DMY có nguồn/
  bằng chứng cột; 511.165 ô vẫn mơ hồ d/m nếu chỉ nhìn chuỗi.
- Parser khảo sát nhận diện số k/tr, tiền có ký hiệu, đơn vị có chữ số và dạng
  `1tr090`; có 9.002 ô dạng ghép triệu trong pass refinement. 160.120 suffix
  đơn vị có cột để đối chiếu khớp cột đơn vị, không mismatch trong pass đó.
  3.746.736 ô numeric còn hai ứng viên dấu phân cách, không gọi là lỗi dữ liệu.
  Min/max số là miền ứng viên, không phải normalized truth đã xác nhận.
- Thử nghiệm arithmetic trên 6 CSV cho thấy phép nhân không đủ chốt locale;
  giảm giá dòng cũng giải thích nhiều chênh lệch, không sửa thành tiền theo
  số lượng × đơn giá. Đây không phải kiểm tra gold hoặc PA.
- 1.095 định nghĩa quy đổi (512 README, 583 bảng), hệ số dương, không xung đột
  trên cùng khóa trực tiếp. Không tự suy hệ số từ chữ số trong tên sản phẩm.
- Quét ngược số lượng cơ bản đã lưu ở 22 business: 1.540.167 dòng đủ thông tin
  có ít nhất một ứng viên số lượng × hệ số khớp chính xác; trong đó 47.334
  dùng hệ số khai báo và 1.492.833 dùng mặc định 1 cho đơn vị có ghi nhưng
  không thuộc đơn vị quy đổi. 256.087 dòng biz_119/120/128 thiếu đơn vị bán,
  không thể kiểm chứng ngược, không gọi là mismatch. Pass đầu đã được sửa
  hai giả thuyết sai: coi không ghi đơn vị là đơn vị cơ bản và bỏ qua nối mã
  sản phẩm với tên trong README. Bằng chứng cuối: quantity_audit_final.json;
  nhiều ứng viên số cùng khớp chưa chứng minh normalization duy nhất.
- Tên sản phẩm có nhiều biến thể dù mã nối đủ; compact tên là thí nghiệm,
  chưa là contract. Khách có phản chứng: ba nhóm tên case/space ở biz_123 gắn
  nhiều mã; thêm một collision ở biz_106 khi bỏ dấu/compact. Không gộp khách
  có mã theo tên.
- 38 nhãn trạng thái đơn thô; chưa nghiệm thu bảng ánh xạ sang 4 trạng thái
  rulebook. Không trộn với status của danh mục khách hàng.
- Đã lập bảng đề xuất đủ 38 nhãn (`status.md`, local). Kiểm tra chéo cơ học
  nhóm returned ở tám business: 2.272 mã trả theo lô ở sáu nhà thuốc và
  350/114 mã lượng âm ở hai sổ, tổng 2.736 mã; nhãn/cờ khớp hai chiều, hỗ trợ
  chín nhãn trả raw. Các nhóm khác vẫn là đề xuất ngữ nghĩa, đặc biệt bốn
  nhãn Không giao được/Đang giao dịch/Đang xử lý/Đã giao cần review. Chưa cài
  bảng này vào inference hay coi là alias contract chung.
- Số dòng nhiều ngày của biz_105/117 liên quan dòng trả âm. Kiểm tra kỹ 114
  mã nhiều ngày ở biz_117: cả 114 có lượng âm sau đọc đúng đơn vị chứa chữ số.
  Không suy thành lỗi tái sử dụng mã đơn; giữ riêng ngày đặt/ngày trả.
- Không thấy U+FFFD/zero-width được kiểm tra; cell text NFC. Heuristic Unicode
  rộng và sáu gán vai trò numeric ban đầu đã được phát hiện là false positive,
  sửa ở lớp báo cáo, giữ pass ban đầu để audit. Không gọi lỗi parser là lỗi data.

## Bằng chứng mới và giới hạn

`verification.json`: 38 kiểm tra pass, gồm bảo toàn partition/cell/type, scoped
context, conversion/quantity/status, Unicode, parser probes, hash raw và validator train mới.
`validate-input.json`: valid=true, gold_content_read=false, exit 0.
Raw 162 file khớp SHA-256 khảo sát đầu. Các script không sửa input hoặc kit manifest.

Cổng CPU chạy mới: `runs/cpu-check-20261105T035816552038Z-53d0njvs/gate.json`:
exit 0, Ruff/format pass, 59 tests pass trong 8.47s, source không đổi trong gate;
đã đọc JSON và ba stage log. Fingerprint source giữ nguyên so với trước khảo sát.
Đây là regression nền; 38 kiểm tra dữ liệu riêng không biến script khảo sát
thành loader được nghiệm thu. Review self-review, không independent agent.
GPU/Modal model không chạy; PA chưa đánh giá.

Lệnh chính đã chạy bằng `.venv/Scripts/python.exe` hoặc uv locked theo README:

```powershell
.tools/uv/uv.exe run --locked python scripts/harness.py context --task A-T1
.tools/uv/uv.exe run --locked python runs/a-t1-deep-survey-20261105/profile_deep.py
.tools/uv/uv.exe run --locked python runs/a-t1-deep-survey-20261105/context_audit.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/relations.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/refine_numbers.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/auxiliary_audit.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/finish_checks.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/arithmetic_probe.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/status_audit.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/quantity_audit.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/quantity_audit.py --refine-context
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/build_report.py
.venv/Scripts/python.exe runs/a-t1-deep-survey-20261105/verify_deep.py
.tools/uv/uv.exe run --locked python scripts/check.py
```

Các lệnh hoàn tất exit 0 ở phiên bản cuối; probe trung gian đã bắt lỗi parser
khi nhầm `25k` thành đơn vị, đã sửa và giữ probe. Source/dependency không đổi;
38 kiểm tra chẩn đoán không thay CPU gate. Artifacts/script có dữ liệu chỉ giữ
trong runs bị ignore, không commit/push/upload.

## Còn mở trước các increment tiếp theo

A-T1 vẫn in_progress: chưa loader DuckDB, structured errors và cache theo
business. Khảo sát đã chạm các câu hỏi A-T2/T3/T4, nhưng chưa nghiệm thu các module.
Trước build loader ghi spec bảo toàn raw/sheet/tọa độ/ID/lỗi; trước cleaning
chốt policy số/ngày/nhóm/dedup và status có nguồn, fixture và regression.

Cardinality profile cột được cap 1.024 giá trị, sau đó báo lower bound; key
counters cho join đếm chính xác. Numeric min/max là bounds trên ứng viên; DMY
không phải kết luận mọi chuỗi ngày tự nó đơn nghĩa. Compact tên không chứng
minh đúng trên schema mới. Ngày có bản ghi không chứng minh dữ liệu đầy đủ;
snapshot cuối kỳ không thay lịch sử. Chưa tính lại lịch âm độc lập.

Đầu vào toàn train đã được xem; gold vẫn chưa parse. Khóa split/access policy
trước tuning/huấn luyện, không mô tả holdout là hoàn toàn chưa từng xem.
