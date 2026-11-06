# Sửa review PR1 — P2a

Ngày06/11/2026, base2ddb03c, cùng nhánh work/p2a-safety. Người dùng yêu cầu
sửa1–6, regression Linux scenarios, gate/CI xanh rồi merge. Đây là increment
hiện hành của P2, không mở model/probe/PA. Quyền merge/push đã được cấp ở yêu cầu này.

## Nguồn, giả thuyết và lựa chọn

Contract submission_runtime yêu cầu /result/submission.jsonl và /result/logs.
RunStore hiện ở root, foreign-dir check từ chối logs; backend_failed gộp lỗi
từng câu với hỏng backend. CLI thiếu fallback; code fingerprint glob bỏ subpackage.
Phép thử: output/logs có trước và q1 timeout nhưng q2–q4 vẫn trả lời thật synthetic.

- Root chỉ chứa submission; logs/submission-<sha>/*.json là log từng câu,
  validator chọn đúng thư mục theo hash final để không lẫn log của attempt cũ.
  Identity/segment/lock/summary/diagnostics chuyển logs/.state. Thư mục rỗng sẵn
  được nhận; file cũ vẫn không ghi đè. Log cuối khớp submission; duration replay
  được gắn timing_available=false, không coi0 là latency đo được.
- Timeout/error của một câu không hỏng backend. Startup_error/worker_exited/
  invalid_worker_result là lỗi backend; hoặc3lỗi liên tiếp. Thành công reset bộ đếm.
  Output budget vẫn có thể dừng backend để giữ headroom cho abstain.
- Giữ run_predict/scoped tooling strict. Submission CLI bọc config+import+run
  bằng Exception, có failsafe prediction-only khi chưa có final. Failsafe đọc
  questions.jsonl, route JSON ID bằng parser cú pháp (không regex), không mở
  answers/business, không tái dùng checkpoint khác identity. ID dedup SQLite
  scratch trên disk và streaming cho >10000IDs/giới hạn inventory. Đường input
  read-only có thể resolve symlink/hardlink; output vẫn không theo link hay
  chạm input. Không thể bảo đảm output khi không đọc được questions hoặc disk
  không ghi được; phải báo lỗi thật, không che lỗi bằng valid=true.
- Fallback final dùng exclusive publication. Hardlink unsupported chỉ ở errno
  capability (EXDEV/ENOSYS/ENOTSUP/EOPNOTSUPP), fallback xb+copy/fsync và nhãn
  non_atomic_exclusive. Không fallback cho disk full/permission; không truncate
  file cũ. Fallback không atomic: chết khi copy có thể để lại final dở, ghi rõ.
  Lựa chọn mới do người dùng yêu cầu thay quyết định cũ fail-closed khi no-link.
- Code hash rglob("*.py") với relative path gồm subpackage; reject code symlink.
- README cập nhật trong commit tài liệu riêng. P2b: resident batching/process
  groups/clock từ shell vẫn deferred; không phát triển model adapter ở đây.

Taxonomy: chỉ đọc cross aggregate dev đã pin SHA trước JSON, user cho phép
dán top20 ô vào hội thoại. Không publish cells/raw records lên GitHub.
