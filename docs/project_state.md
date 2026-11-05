# Trạng thái DataMate

Cập nhật 05/11/2026, giờ Việt Nam. Nguồn kế hoạch duy nhất là DOCX mới,
SHA-256 `b70f5e852b156c7ff0835eebbdd96ccb71b718fd095fd797b554efe5b1837219`; bản đọc [Markdown](../Research/Timeline_DataMate_A-G.md).
Người dùng đã yêu cầu đồng bộ tracker/workspace/GitHub. Kế hoạch tuần 03/11
đã được thay bằng các pha tuần tự P0–P9; A–G là nhóm chuyên môn.

**Bước tiếp theo: P0-SPLIT**, khóa nhóm business/template, split/access policy
và giao thức thống kê trước taxonomy dùng gold. P0-SCORER có thể làm bằng
fixture synthetic trong cùng pha; chỉ một task in_progress. Chỉ mở P1 sau
P0-GATE/G0; sau đó P2 → P3 → P4 → P5 → P6 → P7. P8a/P8b có điều kiện,
cần quyết định chạy/bỏ có lý do trước P9. Chưa triển khai P0 trong phiên đồng bộ.

## Foundation giữ lại

| Task | Trạng thái có bằng chứng | Giới hạn |
|---|---|---|
| A-T1 | done; 30/30 business, 339 unit, 3.997.599 hàng raw; source/cache audit độc lập theo parser | Không semantic cleaning; toàn train input đã được khảo sát |
| A-T2 | done; format/profile/header/data_start/descriptor/consumer; 311 auto, 11 unresolved, 17 SQLite schema; check 218/219 tự chọn, 0 sai | Nhãn cùng tác giả; không unseen QA holdout/PA. data_start chỉ cận dưới; actual descriptor-in-prompt chuyển D-E-T2 → P2 |
| G-FOUNDATION | done_with_limitations; uv/lock, CLI, validators/fake/log/hash, CPU CI và Modal CPU smoke lịch sử | Chưa model thật/GPU, scorer hoặc PA/B0 |

Chi tiết: [A-T1](../reports/a_t1_loader_results.md),
[A-T2](../reports/a_t2_completion_results.md), [foundation](foundation.md).
Source A-T2 `790b1af` có CI lịch sử 144 tests pass
([run 41997216193](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/actions/runs/41997216193)).
Các final acceptance cũ vẫn là evidence lịch sử module; fingerprint cũ không
còn current vì DOCX/harness mới. Không dùng chúng để báo cổng phiên này pass.

## Quyết định hiện hành

- Kiến trúc mục tiêu hybrid: thư viện nghiệp vụ dựng trên dev + model nhỏ gọi
  hàm; SQL/Python dự phòng; abstain/verifier/formatter từ P2. Chưa build kiến trúc.
- Docker tại P3 thuộc G, sau lát cắt P2/G2; giữ draft, chưa build trong migration.
- Gold holdout sealed tới P7. Taxonomy P0 không được lộ gold holdout cho chọn
  prompt/hàm; input đã từng xem phải ghi trong split. Public/private không tuning.
- Mọi model thật chạy Modal, profile `vuonghungnguyen07`, ≤30 USD/thí nghiệm;
  xác minh lại account/budget/quyền dữ liệu trước job. Migration không upload kit.
- Ngày công là ước lượng; quy định/lịch/model/hardware phải xác minh tại task,
  không tự coi nhận định trong Timeline là contract đã xác nhận.
- Legacy converter, multi-table regions và kỹ thuật chưa có lợi ích tiếp tục hoãn.

## Kiểm chứng và archive

CPU cuối: **150 tests pass trong 37.87s**, Ruff/format pass, exit 0;
`runs/cpu-check-20261105T092441563393Z-syph2ikl/gate.json`. Đã đọc record và
ba log; source không đổi trong gate, context CPU passed/current, timeline
sync current, không warning. P0-SPLIT ready; P1 bị chặn bởi P0-GATE.
72 tệp UTF-8/JSON/NFC, 58 link local hợp lệ; 271 protected hashes không đổi.
Kết quả cuối tại [báo cáo](../reports/timeline_sync_results.md).
CPU/Modal model/PA báo riêng; phiên này không chạy model, PA hoặc Docker.

Mốc cũ đã push trước khi dọn: [archive/timeline-20261103](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/tree/archive/timeline-20261103),
commit `bd0061593698df76c05745c7ef1df3d31b1331f3`. Các note reset,
engineering tạm và prompt review đã hết hiệu lực chỉ còn trong archive.
Dữ liệu, cache và run evidence local giữ nguyên; không xóa lịch sử Git.
Quyết định migration: [research note](research/timeline_sync.md).

Phiên mới: `uv run --locked python scripts/harness.py context --task P0-SPLIT`.
Context phải báo nguồn đồng bộ và CPU current trước khi sửa; thiếu/lệch Timeline
thì đồng bộ lại, không fallback sang archive.
