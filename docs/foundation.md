# Foundation giữ lại theo Timeline hiện hành

Đối chiếu 05/11/2026. Đây là bằng chứng module, không phải roadmap thứ hai.

| Thành phần | Bằng chứng lịch sử | Giới hạn và nơi tiếp nối |
|---|---|---|
| A-T1 | [Nghiệm thu loader](../reports/a_t1_loader_results.md): raw/cache, 30 business/339 unit, toàn cell/type/position được đối chiếu | Raw không semantic cleaning; P2/P4 dùng tiếp |
| A-T2 | [Nghiệm thu hoàn thiện](../reports/a_t2_completion_results.md): runtime format/text QA/profile/header/data_start/descriptor; CI 144 tests tại source 790b1af | 11 unresolved, nhãn self-review; prompt/model/PA ở P2; biến thể P7 |
| Contract/validator/stub | [Contract](requirements.md), [machine report lịch sử](../reports/contract_checks.json); output/log train/public đủ id, stub abstain | Scorer bổ sung ở [P0](evaluation.md); nền kế thừa không chứng minh model/B0 |
| CPU harness/CI | Command/log/source hash, fail-fast và stale detection; uv 0.13.6/Python 3.11.18 | Gate phiên nào phải đọc record mới phiên đó; không chứng minh model/evaluation |
| Modal CPU synthetic | Ngày 01/11, app ap-V5mZIojkntGhLow7r8ahUW; hai câu synthetic, block_network, 1 CPU/512 MiB; local runs/modal-cpu-1793514027877932400/ | Chưa GPU/model, throughput, bill hoặc hard spend cap; P1 xác minh lại |

Mọi đầu vào train đã được khảo sát; gold chưa được dùng trong inference.
P0 phải ghi access history khi chia split. Raw/cache/profile/labels/runs giữ
local, không upload lên repo. Hash và kết quả đầy đủ nằm ở evidence task.
Dockerfile/.dockerignore vẫn draft cho P3 sau G2; không build trong migration.
