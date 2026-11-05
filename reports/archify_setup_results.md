# Kết quả setup Archify — 05/11/2026

Ghi nhận cài đặt ban đầu bên dưới là lịch sử. Sau phản hồi người dùng, đã có
[patch local Anh/Việt](archify_language_results.md) cho skill/default renderer;
xem provenance hiện hành trước khi nâng cấp hoặc kiểm nguyên bản upstream.

Đã cài **Archify 3.2.0** vào `.agents/skills/archify/`, commit
`208acba8d412335185b2056fedf54b3405df43fb`, tag `v3.2.0` từ
[repo chính thức](https://github.com/tt-a1i/archify/tree/208acba8d412335185b2056fedf54b3405df43fb).
Skill Installer dùng `--path archify --ref <commit> --dest .agents/skills`.
Release ghim dùng MIT; giữ nguyên license/third-party notices và 203 file
upstream. [Provenance](../.agents/skills/archify/UPSTREAM.json),
[cách dùng/prompt onboarding](../docs/archify.md),
[scope/acceptance](../docs/research/archify_setup.md).

## Kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| File cài so với Git blobs tại commit ghim | 203/203 khớp byte |
| Codex native skills/list forceReload | archify enabled, 0 load error |
| doctor trên Node v26.7.0 | pass, đủ 10 diagram type và explainer |
| demo upstream synthetic | HTML render thành công |
| finalize architecture trên fixture upstream | validate/deliver/check/browser-check đều pass |
| Browser thật | Chrome có sẵn, không tải browser/package |
| Runtime source/config/test/lock | 110 file baseline giữ nguyên |
| Output HTML/receipt | `.archify/` local, gitignore đã kiểm |

Native registry chỉ gọi initialize/initialized/skills/list qua app-server,
analytics/apps/plugins tắt trong tiến trình kiểm; không gọi model, mở thread
hoặc đổi config global. Không npm/pip install, không thêm dependency DataMate.
Đã giữ các thay đổi Superpowers có sẵn trước phiên.

Lệnh kiểm setup:

```powershell
$env:ARCHIFY_UPDATE_CHECK_DISABLED = '1'
node .agents/skills/archify/bin/archify.mjs doctor
node .agents/skills/archify/bin/archify.mjs demo .archify/setup-demo-20261105
node .agents/skills/archify/bin/archify.mjs finalize architecture .agents/skills/archify/examples/web-app.architecture.json .archify/setup-demo-20261105/verified-demo.html --quality showcase --json
.venv/Scripts/python.exe .tmp/archify-setup/verify_install.py
```

Evidence local: `runs/archify-setup-20261105/installation_acceptance.json`,
`registry_rpc.json`, `doctor.log`; artifact/receipt tại
`.archify/setup-demo-20261105/verified-demo.*`.

Đây là demo web-app synthetic upstream, không phải kiến trúc DataMate.
Chỉ kiểm tự động, chưa review cảm nhận hình ảnh; receipt có gợi ý optional về
route nhiều bend. Không thay fixture để che gợi ý. Chưa tạo trang onboarding
DataMate trong setup. Không đọc kit/gold, dùng membership hoặc artifact BTC,
không gọi Modal/model; không có PA/B0/token-savings claim. Tác giả self-review.

Timeline check trả `current`, DOCX SHA-256
`b70f5e852b156c7ff0835eebbdd96ccb71b718fd095fd797b554efe5b1837219`.
CPU: **238 passed in 93.84s (0:01:33)**, Ruff lint/format pass, exit0;
`runs/cpu-check-20261105T150151673404Z-bkz19z94/gate.json`. Đã đọc JSON và
đủ ba log. Context P1 trả passed/current, ready, không planning error/warning;
source hiện hành khớp fingerprint của gate. Không thay trạng thái acceptance:
P0/G0 done, P1 todo/ready, P2 blocked. Không commit/push.
