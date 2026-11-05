# Tích hợp Superpowers cho DataMate

Ngày 05/11/2026. Người dùng yêu cầu cài bộ skill Superpowers cho dự án,
sau khi xác nhận harness DataMate trước đó chưa cài Superpowers.

## Nguồn và phạm vi

- Bài giới thiệu được yêu cầu đọc:
  https://thanhnghiep.top/superpowers-bien-ai-agent-thanh-senior-developer-thuc-thu-va-hoan-toan-mien-phi/
- Nguồn chính thức: https://github.com/obra/superpowers
- Commit khóa: `22f0b463e7a5e579904dd6211a520321035526f7`;
  `.codex-plugin/plugin.json` ghi **7.0.2**, MIT.
- Codex skills/discovery: https://developers.openai.com/codex/skills
- Registry kiểm chứng: https://developers.openai.com/codex/app-server

Upstream hiện hướng dẫn Codex cài plugin qua marketplace; hướng dẫn clone/link
ở `.codex/INSTALL.md` đã không còn (404). Phạm vi người dùng là dự án này:
cài đủ 15 skill gốc và 80 file hỗ trợ vào `.agents/skills/superpowers/` bằng
Skill Installer với --ref ghim commit và --dest project-local. Dùng native
skill discovery, không giả lập một skill Superpowers bằng bản tóm tắt tự viết.
Giữ tên/nội dung/tham chiếu sibling nguyên bản, thêm license và provenance
ngoài các thư mục upstream. Registry phải thực sự nhận đủ 15 skill; nếu layout
nested không được CLI nhận, đổi layout rồi kiểm lại trước khi báo hoàn tất.

## Quyết định tích hợp

Giả thuyết: bộ skill hỗ trợ làm rõ thiết kế, plan, TDD, debug có nguyên nhân,
review và kiểm chứng trước hoàn tất. Setup không chứng minh cải thiện chất lượng
code, token hoặc tốc độ; không chạy model benchmark khi người dùng chưa yêu cầu.

Phương án đã cân nhắc: native plugin theo tài khoản; clone/link global; thư viện
skill theo repo. Chọn thư viện theo repo để phiên bản và hướng dẫn DataMate có
thể review cùng source, không thay cấu hình các dự án khác. Không cài bản rút
gọn ba rule Cursor trong bài giới thiệu vì người dùng yêu cầu Superpowers thật.

AGENTS nối bootstrap `using-superpowers` trước công việc phát triển; không
nhúng toàn bộ 15 skill vào context. Skill Installer giữ các file upstream
nguyên bản. Tên `superpowers:<skill>` trong upstream ánh xạ sang `$<skill>`
của skill local; các đường dẫn tương đối giữa skill được bảo toàn.

DataMate vẫn dùng context/timeline/contract trước implementation, Graphify cho
quan hệ code và state/backlog là tracker duy nhất. Spec/plan là tài liệu thiết
kế, không thay lịch P0–P9 hoặc mở task khác song song. Một increment active;
subagent chỉ trong scope increment và khi skill/người dùng yêu cầu, không giao
gold hoặc mở model job. Dùng tools/model allowlist thật của phiên, không copy
model ID/cú pháp dispatch từ ví dụ upstream khi không khớp runtime.

Các ví dụ npm/pip/poetry/bash trong upstream phải theo stack thực của DataMate:
dependency qua uv/lock, CPU check.py, PowerShell UTF-8, model thật chỉ Modal,
account/budget/data scope trước job. Không xóa code cũ chỉ vì không được viết
bằng TDD, không đổi expected hoặc bỏ test để pass. Chỉ hỏi khi còn quyết định
thiết kế thực sự chưa được chấp thuận; không hỏi lại quyền đã có trong phiên.
Commit/push/merge/xóa worktree tuân theo yêu cầu người dùng và quyền hiện hành.

Optional visual companion và session diagnostic chỉ chạy khi task cần, không
khởi động trong setup; không gửi transcript/gold/kit hoặc tự tạo issue upstream.
Nếu bật visual companion, đặt SUPERPOWERS_DISABLE_TELEMETRY=1 cho tiến trình đó.
Không sửa env/config global hoặc cài model/runtime dependency.

## Acceptance đã chốt trước cài

1. Installer hoàn tất đủ 15 skill, không ghi đè skill DataMate/Graphify.
2. Toàn bộ file upstream khớp Git blob của commit ghim; MIT/provenance đúng;
   YAML metadata hợp lệ, không tên trùng, tham chiếu sibling có đủ.
3. `codex app-server` qua stdio: initialize rồi skills/list nhận đủ 15 tên
   project-local và không lỗi load. Không gọi thread/start hoặc turn/start,
   không gọi model hay đọc kit. Nếu không chạy được, báo đúng giới hạn.
4. Kiểm syntax các script hỗ trợ khi interpreter có sẵn; smoke workspace helper
   trên git repo/plan synthetic riêng, không dùng backlog thật làm input.
5. Timeline current; CPU gate mới pass và source không đổi; đọc JSON/ba log,
   context P1 ready/current. UTF-8/NFC, JSON, link local và diff check.
6. State/backlog chỉ thêm tooling evidence, P1 todo và P2 blocked giữ nguyên.
   Không triển khai P1 model hoặc gọi setup là bằng chứng B0/PA.

Review cấu hình do tác giả thực hiện. Source/raw/gold/kit manifest và split
không thuộc thay đổi này. Bằng chứng local trong runs/superpowers-setup-20261105/;
báo cáo chỉ chứa kết quả cài/kiểm tra, không dữ liệu BTC.

## Điều chỉnh khi kiểm chứng

Gate đầu `runs/cpu-check-20261105T144856840907Z-uqh2ug3u/` lint pass nhưng
format fail: Ruff 0.17.3 muốn đổi code fence Python trong tài liệu upstream
`writing-skills/references/anthropic-best-practices.md`. Chọn giữ byte gốc
và thêm duy nhất `.agents/skills/superpowers` vào tool.ruff.extend-exclude,
thay vì sửa ví dụ vendor. Không loại first-party source/test hoặc đổi expected.
pyproject chỉ đổi cấu hình Ruff; dependency/runtime/uv.lock giữ nguyên.
