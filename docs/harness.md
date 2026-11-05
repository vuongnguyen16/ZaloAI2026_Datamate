# Harness DataMate theo Timeline A–G

Nguồn công việc: `Research/Timeline DataMate theo nhóm việc A–G.docx`.
Tracker duy nhất: `tasks/backlog.json` và `docs/project_state.md`.
Quyết định reset/giữ foundation: `docs/research/timeline_reset.md`.

## Dùng hằng ngày

```powershell
uv run --locked python scripts/harness.py context --task A-T1
uv run --locked python scripts/check.py
```

Chưa có uv PATH thì dùng `.tools/uv/uv.exe` và cache theo README. Dùng skill
repo `$datamate-increment` để research/build/review task đã giao. Không có task
cụ thể thì đọc state và backlog trước khi chọn increment, không tự mở rộng cả nhóm.

Context schema v2 trả `timeline.path/sha256/status`, các file `read_first`, task,
dependency, state và CPU evidence mới nhất. `ready` chỉ nói dependency backlog
đã done. Timeline thiếu phải báo thiếu; không đọc lại plan cũ từ đĩa/Git.
ID cũ không còn trong backlog bị từ chối. Lệnh chỉ đọc, không chạy job.

## Ba cổng kiểm chứng

| Cổng | Yêu cầu | Trạng thái |
|---|---|---|
| CPU | Ruff lint/format + pytest; log, command/exit code, code/test/config/lock hash | `scripts/check.py` hiện có; JSON/log dưới `runs/cpu-check-.../` |
| Modal model | Xác minh account/budget, app/run ID, model revision, hardware/config và lời gọi model thật | D/G chưa có model; smoke CPU lịch sử không thay model gate |
| Evaluation | Scorer theo nguồn E; split/control/config, correct/wrong/abstain/PA và runtime thật | E-T1 và baseline D/E còn todo |

CPU gate không gọi cloud và luôn để GPU/model/PA chưa kiểm chứng. Marker `gpu`
và `modal` bị loại; test cloud không được gọi dịch vụ ở import/collection.
Marker và hướng dẫn không thay thế sandbox thực. Một stage lỗi thì dừng, chuyển tiếp
exit code; pytest trả mã 5 nếu không thu thập được test. Source đổi trong lúc chạy
khiến gate fail.
Context báo record `current` hay `stale`, không tìm một green run cũ để che fail mới.

Fingerprint gồm src/scripts/tests/infra/configs/.agents/.github, pyproject/lock,
.python-version, .gitignore, predict.sh, contract/model manifests và đúng DOCX
timeline. Không đọc kit, credentials hoặc lưu plaintext diff. State/backlog và
tài liệu Markdown vẫn cần review; fingerprint không chứng minh acceptance của chúng.

## Hoàn thành increment

Scope/acceptance phải rõ trong task. Ghi research note trước quyết định kiến
trúc; với bug, cần tái hiện lỗi, xác định nguyên nhân và có regression có ý nghĩa.
Giữ các test về dữ liệu, ID, type và bảo toàn raw; không xóa để làm gate pass.
Review contract/SQL/scorer/
inference có xét leakage, failure paths và tài nguyên; ghi self/independent review.
Chạy gate sau thay code cuối, đọc log/JSON rồi cập nhật state và evidence.

Skill DataMate dùng độc lập; không phụ thuộc plugin workflow bên ngoài hoặc
việc cài Superpowers. Nếu dùng plugin đã cài trong tương lai, phải đọc đúng
skill/version thực và tuân theo phạm vi/nguồn timeline của repo.

CI `.github/workflows/cpu.yml` dùng cùng gate, action pin commit, uv 0.13.6,
Python theo `.python-version`; chỉ upload gate.json và ba stage log synthetic.
Chưa push/chạy Actions thì không báo CI remote đã pass.
