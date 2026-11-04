# Kết quả dọn repo để bắt đầu Timeline A–G

Ngày 04/11/2026, giờ Việt Nam. Thực hiện theo yêu cầu người dùng thay kế hoạch
cũ bằng `Research/Timeline DataMate theo nhóm việc A–G.docx`.
Cleanup đã xong; task chức năng đầu tiên `A-T1` vẫn todo và sẵn sàng bắt đầu.

## Đã bỏ khỏi repo làm việc

Tám file kể tiến độ/review theo roadmap cũ, sau khi gộp phần còn cần vào
`docs/foundation.md`:

- `docs/research/S00_setup.md`
- `docs/research/P00_contract.md`
- `docs/research/P01_inventory_review.md`
- `docs/research/H00_harness_engineering.md`
- `reports/s00_setup.md`
- `reports/p00_results.md`
- `reports/p01_a_results.md`
- `reports/h00_harness_results.md`

Plan cũ đã bị người dùng xóa trước phiên này được giữ nguyên trạng thái xóa.
Không khôi phục nó hoặc duy trì một bản plan song song.

## Đã giữ, chuyển tên và cập nhật

| Thành phần | Phục vụ | Xử lý |
|---|---|---|
| Python/uv/lock, doctor, CPU gate, CI, skill repo | G | Giữ; chuyển hướng skill/AGENTS/harness sang timeline A–G |
| Contracts, strict validation, fake runner, output/log/hash, predict.sh | E/G | Giữ behavior/regression; bỏ nhãn phase cũ khỏi chỉ dẫn code |
| Inventory cơ học | A/T1 một phần | `scripts/inventory_p01.py` → `scripts/inventory.py` |
| Kiểm tra contract | E/G | `scripts/verify_p00.py` → `scripts/verify_contract.py` |
| Regression inventory/validation | A/E/G | Đổi tên thành `test_inventory.py` và `test_structural_validation.py`; giữ các ca và expected hành vi |
| Provenance/contract evidence | E/G | `manifests/p00_sources.json` → `manifests/contract_sources.json`; `reports/p00_contract_checks.json` → `reports/contract_checks.json`; payload lịch sử giữ nguyên |
| Kit manifest/raw, thể lệ và timeline gốc | Dữ liệu/nguồn | Không sửa; hash được kiểm tra |
| Modal config/app và ghi nhận smoke cũ | D/G | Giữ; runbook gọn và history trong foundation; chưa có real model/GPU |
| Dockerfile/.dockerignore | G đóng gói cuối | Giữ nguyên bản nháp; chưa build/test/chỉnh Docker |
| README/state/backlog/requirements/environment/open questions | A–G | Viết lại theo nguồn mới; phân biệt phần kế thừa và phần còn thiếu |

Backlog mới có 20 task theo A–G, bao gồm hai phần nền kế thừa và task reset.
Không chuyển toàn bộ status done cũ sang module mới. Timeline nói scorer “đã có”
được ghi là chưa đúng hiện trạng repo: `E-T1` vẫn todo. Không tạo module rỗng hoặc
build loader/scorer/model trong phiên cleanup.

Context schema v2 trả `timeline` path/hash thay `plan`. Thiếu timeline thì báo
thiếu, không lấy plan cũ trên đĩa hoặc Git. `P01` không còn là task đang hoạt động.

## Backup và phạm vi an toàn

Backup trước sửa/xóa: `runs/timeline-reset-backup-20261104-233607/` (ignored),
32 file đã được copy và đối chiếu SHA-256, gồm cả file chưa commit.
Danh sách/hash trong `backup_manifest.json`. Có thể lấy lại từng file từ đây;
lịch sử Git vẫn giữ nguyên. Backup không chứa bản sao raw data.

Giữ nguyên data, kit manifest, thể lệ, DOCX timeline, `.venv`, công cụ/cache uv,
credentials và run artifacts cũ. Không đụng credential, đổi profile, upload,
commit/push hoặc chạy cloud/model. Những tên phase trong payload nguồn/run cũ
chỉ là lịch sử; không phải chỉ dẫn điều phối mới.

## Kiểm chứng thực tế

Các lệnh uv dùng workspace `.tools/uv/uv.exe`, cache/Python theo README.

| Kiểm tra | Kết quả |
|---|---|
| Regression `test_context_never_resurrects_superseded_plan` trước sửa | Exit 1; thiếu output `timeline`, chứng minh hành vi chưa được triển khai |
| Skill Creator `quick_validate.py .agents/skills/datamate-increment` | Exit 0; Skill is valid |
| `uv run --locked python scripts/check.py` sau sửa | Exit 0; Ruff/format pass, 33 files formatted; **59 passed in 12.07s** |
| `uv run --locked python scripts/audit_kit.py` | Exit 0; Kit hashes unchanged, train/public và thể lệ |
| Context A-T1, task graph, ID cũ | A-T1 todo/ready, timeline working_tree đúng SHA-256, warnings rỗng, CPU passed/current; 20 task không thiếu dependency/vòng lặp; P01 bị từ chối |
| `git diff --check` | Exit 0; không lỗi whitespace |

Gate artifact:
`runs/cpu-check-20261104T164734905777Z-5kmhmukp/gate.json` và ba log cạnh file.
Context artifact: `runs/timeline-reset-context.json` (local, ignored).
Timeline SHA-256:
`e74b1292119f01ca3eae7d20d709921219efc30e655e01909685c50d5363eb51`.

58 regression hiện có được giữ; một test mới bảo vệ yêu cầu bỏ plan cũ.
Test context cũ được cập nhật theo contract timeline mới do người dùng yêu cầu,
không bỏ các ca fail-fast, source mutation, stale evidence hoặc bảo vệ gold/raw.
Review là self-review, chưa review độc lập. GPU/model không chạy; PA chưa đánh giá;
CI trên GitHub chưa chạy. Không tuyên bố hiệu quả model hoặc hoàn thành A–G.

## Điểm bắt đầu tiếp theo

Chạy `uv run --locked python scripts/harness.py context --task A-T1`, đọc timeline
A/T1 và requirements. Increment kế tiếp là khảo sát metadata và thiết kế loader
giữ raw; E-T1 scorer và C-T1 rulebook/calendar vẫn là các việc nền cần làm tiếp.
