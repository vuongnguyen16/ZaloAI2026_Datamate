# Superpowers trong DataMate

Đã cài bộ **15 skill Superpowers 7.0.2** từ
[obra/superpowers](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7),
ghim commit `22f0b463e7a5e579904dd6211a520321035526f7`, MIT.
Các file upstream giữ nguyên trong `.agents/skills/superpowers/`, cùng
[provenance](../.agents/skills/superpowers/UPSTREAM.json) và
[license](../.agents/skills/superpowers/LICENSE).

Đây là cài **thư viện skill theo repo** bằng Skill Installer, không phải plugin
marketplace theo tài khoản. Native Codex skill discovery nạp metadata; chỉ đọc
body khi skill được dùng. AGENTS.md yêu cầu bootstrap using-superpowers trước
công việc phát triển, không nhúng cả thư viện vào mọi prompt.

## Cách dùng

Skill có thể được chọn theo yêu cầu hoặc gọi trực tiếp từ lượt tiếp theo:

| Nhóm | Skill local |
| --- | --- |
| Bootstrap | `$using-superpowers` |
| Ý tưởng và thiết kế | `$brainstorming` |
| Lập và thực thi plan | `$writing-plans`, `$executing-plans` |
| Test và debug | `$test-driven-development`, `$systematic-debugging` |
| Kiểm chứng | `$verification-before-completion` |
| Review | `$requesting-code-review`, `$receiving-code-review` |
| Workspace và bàn giao | `$using-git-worktrees`, `$finishing-a-development-branch` |
| Subagent | `$subagent-driven-development`, `$dispatching-parallel-agents` |
| Bảo trì skill/workflow | `$writing-skills`, `$diagnosing-superpowers` |

Ví dụ: “Dùng `$systematic-debugging` tìm nguyên nhân lỗi này” hoặc
“Dùng `$brainstorming` thiết kế lát cắt P2 theo acceptance hiện tại”. Các tên
`superpowers:<skill>` trong upstream tương ứng `$<skill>` ở cài đặt local.
Không cần cài thêm bản global hoặc gắn namespace plugin vào tên local.

Luồng thường dùng: context DataMate → using-superpowers/skill phù hợp →
thiết kế và plan khi cần → test trước cho thay đổi hành vi → triển khai →
review → CPU gate và handoff. Không dựng lại spec đã được duyệt hoặc hỏi lại
quyền đã có chỉ để lặp checklist. Chưa rõ quyết định có ảnh hưởng thiết kế thì
hỏi đúng điểm đó; yêu cầu đã rõ thì tiếp tục trong scope.

## Hòa hợp với repo

- `datamate-increment` giữ timeline/contract/task/evidence; Graphify dẫn đường
  cho câu hỏi liên kết nhiều file. Các skill này tiếp tục được giữ nguyên.
- State/backlog là tracker duy nhất. Spec/plan dùng `docs/research/` theo
  quy định DataMate, không tự mở roadmap hoặc triển khai pha khác.
- Một increment active; subagent chỉ làm phần thuộc scope khi workflow yêu cầu.
  Áp dụng allowlist model/tools thực của phiên, không dùng tên ví dụ upstream.
- Mọi model DataMate/embedding/reranker/training vẫn chỉ Modal. Cài skill không
  cho phép job, đọc gold hoặc gửi dữ liệu. Diagnostic/export không tự gửi
  transcript/kit lên dịch vụ hoặc issue upstream.
- Ví dụ setup Python trong upstream phải đổi sang uv/lock; local chỉ CPU
  nhẹ/synthetic. Cổng chuẩn vẫn `uv run --locked python scripts/check.py`.
- Test-first áp dụng thay đổi hành vi; giữ nguyên code/test hiện có. Không xóa
  code vì lý do lịch sử TDD hoặc giảm expected để pass. Đổi cấu hình/MD dùng
  kiểm tra thích hợp, không tạo test chỉ phản chiếu nội dung file.
- Review/finishing không mở quyền commit/push/merge/xóa ngoài yêu cầu đã có.
  Worktree mới không có artifact ignored; nếu task cần dữ liệu thì xác minh
  source/mount theo policy, không chia lại split hoặc tự copy gold sang đó.

Các helper SDD dùng Bash. Windows dùng Git Bash
`C:/Program Files/Git/bin/bash.exe`, không dùng `bash.exe` shim WSL.
Visual companion là tùy chọn và không chạy trong setup; nếu bật, đặt
`SUPERPOWERS_DISABLE_TELEMETRY=1` cho tiến trình đó. Không có telemetry service,
hook, package install hay thay đổi model/config global do setup này tạo ra.

## Update và kiểm chứng

Không auto-update. Review commit mới trước, giữ đủ các sibling skill/support
files và MIT, cập nhật provenance sau khi so diff. Installer không ghi đè thư
mục đã có; chuẩn bị output mới để kiểm rồi thay đúng bộ đã xác minh.
Ruff bỏ qua đúng thư mục vendor `.agents/skills/superpowers` để giữ byte
upstream; toàn bộ first-party source/test vẫn thuộc gate bình thường.

Registry `codex app-server`/skills/list được dùng để kiểm Codex nhận đủ skill,
không gọi model. CPU gate chỉ chứng minh regression suite; không chứng minh
chất lượng hành vi hoặc mức tiết kiệm token của Superpowers.
[Quyết định và acceptance](research/superpowers_setup.md),
[báo cáo nghiệm thu](../reports/superpowers_setup_results.md).
