# P2a CPU safety và bảng chéo taxonomy dev

Ngày06/11/2026, branch `work/p2a-safety`, base `4dbe1c8`.
Thiết kế: [p2a_safety_design](../docs/research/p2a_safety_design.md);
[plan triển khai](../docs/research/p2a_safety_plan.md).
Bản này ghi nghiệm thu ban đầu. Thay đổi sau phản hồi Linux PR1 nằm ở
[báo cáo sửa review](p2a_review_fixes_results.md), không dùng gate cũ cho source mới.

## Kết quả và phạm vi

Đã triển khai serializer chính xác cho9type, Decimal/large integer không qua
float, percent HALF_UP, validate bytes cuối bằng parser/validator scorer.
Writer smoke/stub dùng cùng serializer; scorer/policy cũ giữ nguyên.

`datamate predict` và `predict.sh` dùng coordinator CPU `no_model`, mặc định
abstain. Một dòng lỗi không làm mất ID khác; JSON hỏng không được đoán ID.
ID trùng cùng payload gộp, xung đột abstain. Checkpoint segment riêng từng
invocation, fsync từng câu, OS single-writer lock, identity input/config/code/model.
Resume khớp identity; conflict giữ nguyên file cũ và giữ candidate pending.
Publish dùng fsync file + hardlink độc quyền, không fallback ghi đè.

Deadline bắt đầu khi package application được nạp trước CLI imports/data/model;
không phải timestamp OS sinh process. Có reserve finalize, worker CPU giới hạn
từng câu. Backend lỗi/timeout chuyển phần còn lại abstain. DuckDB trusted query
chạy process riêng, read-only/external access tắt,2threads/256MiB, kết quả bounded,
interrupt rồi terminate/kill/join. Không phải SQL fallback cho model.

Windows thiếu portable directory fsync: báo rõ `unavailable_windows_process_crash_only`.
Kiểm chứng kill/resume là process crash, chưa bảo đảm khi mất điện. P3 phải thử
hardlink/fsync trên Linux filesystem `/result` thật. Backend CPU batchsize1 chưa
là adapter model resident; P2b/P3 phải triển khai vòng đời offline phù hợp.

## Bảng chéo đã chạy

Lệnh: `uv run --locked datamate taxonomy-cross --split runs/p0-split-20261105/frozen
--manifest-sha256 b28dd4fa7fb34b7a0ed356c7ec11f32f84911bcdf71fcd128c2c5082b208fa18
--output runs/p2a-taxonomy-cross-20261106`.

Authorize context dev trước giải mã; SHA artifact phải khớp proof P0 trước parse.
Không mở `answers.jsonl`, không decode gold calibration/holdout; không xuất
ID/text/answer/alias vào cross. Nhãn family/operation/time là heuristic P0,
expected_type từ taxonomy dev đã được phép; chưa human-reviewed accuracy.

Artifact local ignored: `runs/p2a-taxonomy-cross-20261106/cross.json`, `report.md`.
SHA256 cross: `17ebe362799632077d891ab55569ba2b1773e14da94c004e0b29d38c3f4f01c0`.
Nguồn taxonomy: `e1cd00a41c741203c3d5bf1350a8774fa840a0fe7176090277c49cc74da262f1`.
Unique1895, cells199, Cartesian memberships2589; tổng ô không phải tổng câu.
Chi tiết ô và membership không commit/push.

## Kiểm chứng

55test mới pass trong gate cuối: serialization23, store9, worker5,
prediction10, cross8. Trước review,47targeted pass; sau fix,54targeted pass
và regression reserve riêng pass, rồi toàn suite cuối pass.
Ca thực gồm truy vấn DuckDB/Decimal, external-access/write denial, interrupt,
forced terminate và child cleanup; race file đích, unsupported hardlink, torn
journal, duplicate/conflict, resume fingerprint mismatch, CLI kill/resume2000IDs.
Synthetic guard cấm mở gold trong cross-reader, kiểm hash-before-decode.
Review độc lập source/synthetic một lượt phát hiện6Important. Đã sửa với
regression RED→GREEN: init trước manifest, numeric parse/accounting ID,
duplicate khác thứ tự key, IPC không unpickle kết quả, aggregate output/journal.
Thêm streaming recovery chống quá nhiều dòng hỏng và chứa InvalidOperation
trong journal. Đồng bộ default reserve120s được nâng thành Important và có
regression riêng; strict UTF-8 được xử lý cùng syntax-only ID projection.
Không chạy lại reviewer sau fix; tác giả kiểm regression và toàn CPU suite.

CPU cuối: `uv run --locked python scripts/check.py`, exit0, Ruff/format pass,
**369passed,1skipped trong85.94s**. Skip symlink fixture vì quyền Windows.
`runs/cpu-check-20261106T140338585948Z-ltr1oldz/gate.json`, source không đổi
trong gate. Đã đọc JSON và cả3log; fingerprint
`aaa6eedba5b0732abb78a739ed2fe1e16d75e4bf820dce30c14016001d5b398f`.
Timeline current, Graphify current812nodes/2679edges/73files. Context P2
passed/current, dependency ready, không planning error/warning/active task khác;
P2 là task in_progress duy nhất. CPU không là G2/PA.

Minor README tools của bản đầu đã được sửa trong commit tài liệu riêngf33bf08
theo phản hồi PR1; xem báo cáo sửa review cho trạng thái hiện hành.

## Quyết định và giới hạn review

- Triển khai inline ngay theo yêu cầu, không hỏi lại thiết kế; nếu hiểu sai sẽ
  phải làm lại phần code, không mở thêm phạm vi GPU.
- Windows báo thiếu directory fsync; chỉ process-crash, chưa power-loss guarantee.
- Đổi writer cũ sang serializer chung để nhận Decimal; byte formatting cũ đổi,
  có regression contract/scorer bảo vệ.
- Backend CPU batch1/process riêng chỉ là đường nối P2a; model resident là P2b/P3,
  throughput thật chưa được kiểm chứng.
- Clock từ package init bao gồm CLI imports/data/model, chưa bao gồm interpreter bootstrap.
- Custom proof chỉ cho namespace synthetic; taxonomy thật cần cập nhật provenance
  được xem xét riêng, không truyền metadata tùy ý qua CLI.
- Model/prompt/cleaning/PA/G2 ngoài increment; chưa có bảo đảm chất lượng thật.
- Tác giả kiểm hash/aggregate thật, reviewer không đọc BTC; heuristic accuracy chưa xác nhận.
- CPU freshness do tác giả kiểm đầy đủ, bằng chứng chỉ cho môi trường Windows này.
- Hardlink/fsync mount Linux và power-loss vẫn kiểm P3; portability còn pending.
- Python caller hoặc ancestor swap ác ý ngoài OS boundary; đây không là sandbox hostile code.
- Cleanup chỉ direct worker; adapter thật cần quản lý cả process tree.
- Giới hạn lớn kiểm bằng budget rút nhỏ; chưa stress multi-GiB thật.

Chưa model/Modal job, prompt/cache spec P2b, context/throughput probe dev,
cleaning/domain_lib P2c, PA dev, public submission hoặc Docker/P3. P2 in_progress.
G5/split/timeline hash và quyền dữ liệu đã chốt giữ nguyên; không mở task P3.
