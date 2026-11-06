# P2a — cô lập timeout và bỏ qua mục output ngoài runner

Ngày06/11/2026. Nguồn: phản hồi/xác nhận người dùng sau PR1, contract
submission_runtime và acceptance P2. Không đổi G2, split/scorer/G5.

Hai lỗi đã tái hiện trên e17a14b: lost+found làm submission bị từ chối;
ba timeout liên tiếp khiến backend_unavailable cho các ID sau.

Quyết định: runtime chỉ kiểm các đường dẫn nó quản lý (logs/submission);
mục khác chỉ ghi tên vào diagnostics, không stat/resolve/open/xóa nội dung.
Không nới guard cho output root, logs, final hoặc lock; private checkpoint vẫn
strict. Giữ một writer và không overwrite file cũ.

Timeout hoặc query error không chứng minh backend chết, bất kể số lần lặp.
Chỉ startup_error, worker_exited, invalid_worker_result mới vô hiệu backend.
Global deadline/output budget vẫn bảo vệ toàn lượt; chưa thêm circuit breaker.
Nếu thêm sau phải có health check và half-open, không khóa vĩnh viễn theo timeout.

Phép thử: lost+found/user file không được đọc hay sửa; alias ở mục ngoài runner
được bỏ qua; logs/final alias vẫn bị từ chối; ba timeout/error không chặn câu
tiếp theo; startup/dead/protocol failure vẫn ngừng backend; writer đang chạy
vẫn chặn invocation khác. Chỉ synthetic/CPU, không gold/model/data mới.
