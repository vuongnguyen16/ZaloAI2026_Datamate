# Harness DataMate theo Timeline A–G

Nguồn công việc: `Research/Timeline DataMate theo nhóm việc A–G.docx`.
Tracker duy nhất: `tasks/backlog.json` và `docs/project_state.md`.
Lộ trình một người, tuần tự P0–P9; A–G là nhóm chuyên môn.
Quyết định đồng bộ/giữ foundation: `docs/research/timeline_sync.md`.

## Dùng hằng ngày

```powershell
uv run --locked python scripts/timeline.py check
uv run --locked python scripts/harness.py context --task P2
uv run --locked python scripts/check.py
```

Chưa có uv PATH thì dùng `.tools/uv/uv.exe` và cache theo README. Dùng skill
repo `$datamate-increment` để research/build/review task đã giao. Không có task
cụ thể thì đọc state và backlog trước khi chọn increment, không tự mở rộng cả nhóm.

Context schema v3 trả `timeline.path/sha256/status/sync_status`, các file
`read_first`, task/dependency, `planning_errors`, state và CPU evidence mới nhất.
`ready` cần nguồn/bản web/asset/tracker đồng bộ, graph hợp lệ và dependency
done; không chứng minh acceptance. Optional chỉ được giải quyết khi done hoặc
skipped kèm lý do. Tối đa một task in_progress; task khác không ready khi còn
việc đang làm. ID tuần cũ bị từ chối; mapping trong `manifests/timeline_source.json`.
Timeline thiếu/lệch nguồn chặn readiness, không fallback đĩa/Git.
Lệnh chỉ đọc, không chạy job.

Khi DOCX đổi: đọc nguồn → đối chiếu scope/acceptance/dependency →
`python scripts/timeline.py export` → cập nhật manifest/tracker/state/hướng dẫn
→ `timeline.py check` → CPU gate. Export không tự xác nhận tracker đã đúng và
không xóa asset cũ; phải review/dọn asset hết hiệu lực. Manifest chỉ ghi nguồn/
hash/mapping lịch sử, không phải tracker thứ hai.

## Ba cổng kiểm chứng

| Cổng | Yêu cầu | Trạng thái |
|---|---|---|
| CPU | Ruff lint/format + pytest; log, command/exit code, code/test/config/lock hash | `scripts/check.py` hiện có; JSON/log dưới `runs/cpu-check-.../` |
| Modal model | Xác minh account/budget, app/run ID, model revision, hardware/config và lời gọi model thật | P1/G1 đã có hai model thật sm_120/offline/synthetic; xem reports/p1_results.md; chưa PA/B0 |
| Evaluation | Project scorer từ nguồn E, scoped reader, split/control/config/log/bootstrap | P0/G0 đã có; model/PA baseline hybrid P2 còn todo |

CPU gate không gọi cloud và luôn để GPU/model/PA chưa kiểm chứng. Marker `gpu`
và `modal` bị loại; test cloud không được gọi dịch vụ ở import/collection.
Marker và hướng dẫn không thay thế sandbox thực. Một stage lỗi thì dừng, chuyển tiếp
exit code; pytest trả mã 5 nếu không thu thập được test. Source đổi trong lúc chạy
khiến gate fail.
Context báo record `current` hay `stale`, không tìm một green run cũ để che fail mới.

Fingerprint gồm src/scripts/tests/infra/configs/.agents/.github, pyproject/lock,
config Graphify và pyproject/lock riêng tại tools/graphify (không hash .venv tool),
.python-version, .gitignore, predict.sh, contract/model manifests và đúng DOCX
timeline cùng timeline manifest, bản web, asset và backlog. Không đọc kit,
credentials hoặc lưu plaintext diff. State và tài liệu khác vẫn cần review;
fingerprint không chứng minh acceptance của chúng.

P0 khóa split/access trước taxonomy gold. G0 mới mở P1, rồi P2 → P3 đóng gói
thuộc G → P4–P7; P8a/P8b có điều kiện, quyết định chạy/bỏ trước P9.
Giữ Docker draft trước G2; Modal Image phục vụ P1. P7 chỉ mở gold holdout một
lần; cải tiến sau đó cần công bố giới hạn hoặc có đánh giá độc lập mới.

## Hoàn thành increment

Scope/acceptance phải rõ trong task. Ghi research note trước quyết định kiến
trúc; với bug, cần tái hiện lỗi, xác định nguyên nhân và có regression có ý nghĩa.
Giữ các test về dữ liệu, ID, type và bảo toàn raw; không xóa để làm gate pass.
Review contract/SQL/scorer/
inference có xét leakage, failure paths và tài nguyên; ghi self/independent review.
Chạy gate sau thay code cuối, đọc log/JSON rồi cập nhật state và evidence.

Skill DataMate giữ context/contract/gate của dự án. [Superpowers](superpowers.md)
7.0.2 đã cài đủ 15 skill project-local, bootstrap bằng using-superpowers trong
AGENTS.md; đọc đúng skill/version trước dùng. Superpowers hỗ trợ quy trình,
không thay timeline, state/backlog, scoped data hoặc cổng CPU/Modal/PA.
Spec/plan là thiết kế của task hiện hành trong docs/research/, không tracker mới.

CI `.github/workflows/cpu.yml` dùng cùng gate, action pin commit, uv 0.13.6,
Python theo `.python-version`; chỉ upload gate.json và ba stage log synthetic.
Chưa push/chạy Actions thì không báo CI remote đã pass.

P0-SPLIT đã khóa tại `manifests/split_lock.json`; pointer được đưa vào CPU
fingerprint. Artifact BTC/membership chỉ local trong runs; CPU CI dùng fixture
synthetic, không cần kit. Trước real-gold evaluation chạy `datamate split-check`
theo `docs/split_policy.md`; P0-SCORER đã nối scoped reader/evaluator vào guard.
Gold holdout không được release bởi lệnh P0, chỉ có giao thức cho P7.
