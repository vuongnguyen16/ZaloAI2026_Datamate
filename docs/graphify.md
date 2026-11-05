# Graphify cho Codex

Graphify `0.9.102` đã được khóa trong `tools/graphify/pyproject.toml` và
`tools/graphify/uv.lock`, có `.venv` riêng. Package chính thức là `graphifyy`
(hai chữ y), command upstream là `graphify`. Runtime DataMate không thêm dependency.
[Quyết định/phép thử](research/graphify_setup.md).

## Sử dụng

Từ thư mục gốc repo, sau context bắt buộc theo AGENTS:

```powershell
.venv/Scripts/python.exe scripts/graphify_local.py status
.venv/Scripts/python.exe scripts/graphify_local.py query "run_eval read_scoped" --budget 1200
.venv/Scripts/python.exe scripts/graphify_local.py explain "read_scoped"
.venv/Scripts/python.exe scripts/graphify_local.py path "run_eval" "score"
```

Trong Codex, có thể gọi `$graphify` hoặc viết: “Dùng graph để tìm luồng gọi
run_eval → read_scoped, rồi đọc các hàm liên quan”. Skill repo được phát hiện tự động;
nếu chưa xuất hiện, khởi động lại phiên Codex. AGENTS đã có hướng dẫn tra cứu
graph cho câu hỏi kiến trúc/nhiều file. Không cần sửa cấu hình Codex global,
bật multi-agent hoặc nối MCP.

`query` mặc định budget khoảng 1.200 token, depth 1; tăng có chủ đích tới
4.000/depth 3 khi thiếu ngữ cảnh. Đây là ước lượng output, không phải billing cap
hoặc giới hạn toàn bộ context Codex. Dùng tên symbol tiếng Anh để match AST;
câu tiếng Việt có thể kém recall. Query một lần rồi đọc source cần sửa.
`explain`/`path` giải quyết tên trùng bằng yêu cầu chọn node ID; CLI trả mã 3
khi mơ hồ, 4 khi không tìm thấy. Dùng rg nếu graph không đủ thông tin.

## Cập nhật và cài lại

```powershell
.venv/Scripts/python.exe scripts/graphify_local.py update
.venv/Scripts/python.exe scripts/graphify_local.py html
```

`build` dùng lần đầu; `update` và `build` đều tận dụng incremental/cache của
Graphify. Không rebuild mỗi câu hỏi. Wrapper từ chối query khi fingerprint
code/config hoặc hash graph thay đổi; update một lần khi cần tra cứu lại sau sửa.
HTML tùy chọn ở `graphify-out/graph.html`, không cần mở để agent query.
Đồ thị và receipt/cache giữ local trong `graphify-out/`, đã gitignore.

Máy/clone mới: cài môi trường DataMate theo README, rồi:

```powershell
$env:UV_CACHE_DIR = "$PWD/.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD/.uv-python"
.tools/uv/uv.exe sync --project tools/graphify --locked
.venv/Scripts/python.exe scripts/graphify_local.py build
```

Không cần đưa `graphify` lên PATH. CLI upstream nằm trong
`tools/graphify/.venv/Scripts/`, nhưng dùng wrapper để giữ cấu hình local.
Không chạy `graphify install` để ghi lại skill/AGENTS mặc định dài hơn.

## Phạm vi và giới hạn

Chỉ code Python trong `src/`, `scripts/`, `tests/`, `infra/` được lập chỉ mục.
`.graphifyignore` mặc định loại mọi thư mục gốc khác; wrapper còn truyền exclude
tường minh cho chúng, tắt backend LLM và query log global, giới hạn hai worker
và hai CPU threads. Wrapper từ chối symlink/junction trong cây code.
Không có cloud, API key, weights, embedding, CUDA hoặc LLM extras.

Docs/timeline/contract/tracker, fixtures, BTC data/gold, reports/runs, manifests,
credentials và môi trường không nằm trong graph. Khi cần chúng, đọc nguồn
được phép theo AGENTS/scoped reader. Graph không thay quyền đọc gold hoặc
chứng minh acceptance. AST có thể thiếu dynamic dispatch và có inferred edges;
đọc source trước sửa, kiểm CPU sau thay đổi. Đây là allowlist công cụ,
không phải OS ACL hoặc sandbox chống mọi hành vi của package bên thứ ba.

Chưa đo A/B token thực tế trên phiên Codex, chưa cam kết mức giảm phần trăm.
Build AST không dùng token LLM; query vẫn tiêu thụ token khi output vào context.
Đã có [replay đo nội dung truy xuất cho một audit phức tạp](../reports/graphify_token_benchmark.md):
graph giảm77,80% so đọc toàn49 file, giảm27,21% so rg đọc nguyên file liên quan,
nhưng tăng12,22% so rg chỉ đọc cùng các đoạn source. Tokenizer o200k_base tham
chiếu; đây chưa phải billing hoặc hai phiên agent độc lập. Không suy ra mức
tiết kiệm trung bình từ một câu hỏi.
Có thể vô hiệu hóa bằng bỏ hướng dẫn Graphify khỏi AGENTS và chuyển skill repo
ra ngoài `.agents/skills`; không ảnh hưởng runtime DataMate.
