# Kết quả setup Superpowers cho DataMate

Ngày 05/11/2026, giờ Việt Nam. Người dùng yêu cầu cài Superpowers cho dự án.
Đã cài **7.0.2**, commit `22f0b463e7a5e579904dd6211a520321035526f7`,
[source chính thức](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7).
[Hướng dẫn](../docs/superpowers.md), [quyết định/acceptance](../docs/research/superpowers_setup.md),
[provenance](../.agents/skills/superpowers/UPSTREAM.json),
[MIT](../.agents/skills/superpowers/LICENSE).

## Đã kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| Skill Installer, --ref và --dest project-local | Đủ 15 skill, không ghi đè hai skill hiện có |
| File upstream so với Git blob của commit | 80/80 byte-equivalent, metadata YAML hợp lệ |
| Native Codex registry, forceReload=true | 15/15 enabled, 0 load error, layout nested được nhận |
| Bash/Node syntax checks | 12 script pass |
| sdd-workspace trên git repo/plan synthetic | exit0, workspace và ignore file tạo đúng trong scratch |
| Source/config/test/lock và hai skill cũ | 69 hash giữ nguyên; pyproject chỉ thêm Ruff vendor exclusion |
| Model calls trong kiểm registry/helper | 0; chỉ initialize/initialized/skills/list |

Native registry được gọi bằng `codex app-server --stdio`, analytics=false,
apps/plugins tắt cho tiến trình kiểm. Không gọi thread/start/turn/start hoặc
thay config global. Đây là kiểm Codex thực sự phát hiện skill, không chỉ
kiểm file đã tồn tại. Skill có thể được dùng trong lượt tiếp theo; nếu UI chưa
hiện, mở lại phiên để tải catalog mới.

Đã giữ nguyên cả thư viện upstream trong `.agents/skills/superpowers/`, nối
bootstrap vào AGENTS.md, cập nhật README/harness và hướng dẫn hòa hợp DataMate.
Đây là thư viện skill repo-scoped, không phải native marketplace plugin theo
tài khoản. Các workflow gốc và tài nguyên hỗ trợ được giữ, không thay bằng
vài rule tự viết. Các chỉ dẫn DataMate/người dùng có ưu tiên khi xung đột.

Không có production code/logic model thay đổi trong setup. Không cài package
runtime, CUDA/weights hoặc mở Modal job. Không đọc kit/gold, đổi split hoặc
chạy evaluation BTC. P0/G0 giữ done, P1 todo/ready, P2 blocked. Spec/plan chỉ
là tài liệu thiết kế cho task hiện hành, không tracker/roadmap mới.

## Giới hạn

Review do tác giả thực hiện, không independent reviewer. Registry/syntax/helper
smoke không chứng minh chất lượng reasoning, TDD adherence hoặc token savings
của một phiên LLM. Chưa chạy workflow coding agent hoặc pressure eval của
upstream. Visual companion/diagnostic export không chạy trong setup; nếu
dùng visual companion phải đặt SUPERPOWERS_DISABLE_TELEMETRY=1 theo hướng dẫn.
Code helper dùng Git Bash trên Windows; bash.exe shim WSL không được dùng.

## Lệnh và evidence

```powershell
.venv/Scripts/python.exe runs/superpowers-setup-20261105/verify_install.py
.tools/uv/uv.exe run --locked python scripts/timeline.py check
.tools/uv/uv.exe run --locked python scripts/check.py
.tools/uv/uv.exe run --locked python scripts/harness.py context --task P1
```

Lệnh installer dùng repo obra/superpowers, --ref đúng commit trên, 15 đường dẫn
skills/* và --dest .agents/skills/superpowers. Chi tiết command và hashes trong
provenance/driver local; installer không ghi đè thư mục đã tồn tại.

Evidence local/ignored: `runs/superpowers-setup-20261105/installation_acceptance.json`,
`registry_rpc.json`, `registry.stderr.log` và `synthetic-workspace/`.
Source hiện hành đã qua timeline check. CPU cuối: **238 passed in 124.97s (0:02:04)**, Ruff/format
pass, exit0; source không đổi trong gate. `runs/cpu-check-20261105T145024412015Z-vo2acxq5/gate.json`.
Đã đọc JSON và đủ ba log; context P1 passed/current, ready/no warnings.
Bằng chứng CPU cũ chỉ là baseline trước cài.

Gate đầu `runs/cpu-check-20261105T144856840907Z-uqh2ug3u/` lint pass, format
fail vì code fence trong tài liệu vendor; pytest chưa chạy. Đã giữ nguyên
upstream và loại đúng `.agents/skills/superpowers` khỏi Ruff, không bỏ code/test
DataMate. pyproject chỉ thêm tool.ruff.extend-exclude, dependency/uv.lock không đổi.

Đã dùng TinyFish Research cho bài tham khảo/source, Skill Installer cho thư
viện, OpenAI Docs cho discovery/registry và DataMate increment cho gate/scope.
