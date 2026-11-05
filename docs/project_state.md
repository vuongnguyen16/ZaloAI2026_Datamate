# Trạng thái DataMate

Cập nhật 05/11/2026, giờ Việt Nam. Timeline DOCX là nguồn kế hoạch duy nhất,
hash `b70f5e852b156c7ff0835eebbdd96ccb71b718fd095fd797b554efe5b1837219`;
[bản đọc](../Research/Timeline_DataMate_A-G.md). A–G là chuyên môn, P0–P9 tuần tự;
tracker duy nhất state và tasks/backlog.json.

**P0/G0 đã hoàn tất.** Split/scorer/taxonomy/gate đều done;
P1 ready, chưa model/Modal/Docker/public submission. P1 phải xác minh
model/license/cutoff/tổng ≤15B, runtime sm_120, account vuonghungnguyen07,
budget ≤30 USD và phạm vi dữ liệu trước job. Không tự mở job để chốt P0.

## P0 hiện hành

- Split 18/6/6 business, 1895/397/708 câu, 4/3/2 cụm độc lập. Manifest hash
  `b28dd4fa7fb34b7a0ed356c7ec11f32f84911bcdf71fcd128c2c5082b208fa18`
  giữ nguyên; [split policy](split_policy.md). Không chia lại sau xem gold.
- Scorer 9 type, run_eval/log, scoped reader, hashes và paired bootstrap
  business/leakage sensitivity đã có; corner policies provisional.
  [Hướng dẫn](evaluation.md), [nghiệm thu](../reports/p0_results.md),
  [provenance](../manifests/p0_evidence.json).
- Taxonomy metadata3000/dev1895; calibration397/holdout708 sealed. Dev34
  unanswerable, 519 ASCII-only, 157 other/456 multi-candidate. Type từ gold dev;
  họ/time/viết tắt heuristic, không human-reviewed accuracy claim.
- Shared gold file được đọc byte/ID để routing; chỉ decode type/answer/alias
  dev. Acceptance ngoài dev=0, live sealed-denial pass; release/public ledger
  rỗng. Không gọi đó là chưa mở file gold; không xuất gold answer/alias.
- All-abstain PA0 chỉ contract probe, không model/B0; runtime inference
  unavailable. Calibration aggregate path kiểm synthetic, chưa phân tích gold
  calibration. Ít leakage groups nên không significance claim.
- API không thay OS ACL; release P7 cần evaluator/gate/prediction freeze riêng.

Artifact thật chỉ local trong runs/p0-complete-20261105/. 161 source file,
split và kit manifest không đổi; contract registry chỉ đồng bộ3 trường project,
không đổi luật BTC. Không commit/push; CI cũ không chứng minh source mới pass.
CPU cuối **232 tests pass trong36.59s**, Ruff/format pass, exit0;
`runs/cpu-check-20261105T113049158829Z-92zldnf2/gate.json`. Đã đọc JSON/ba log,
source không đổi trong gate, context passed/current/no warnings. Final proof
`runs/p0-complete-20261105/final_acceptance.json` valid=true, source/artifacts
current; gold byte hash khớp kit gốc, semantic decode ngoài dev=0. 92 tệp
UTF-8/NFC/JSON và83 link local hợp lệ, luật BTC không đổi. P1 ready, P2 blocked.

## Foundation và ràng buộc giữ lại

A-T1 [loader](../reports/a_t1_loader_results.md) và A-T2
[format/profile/header/descriptor](../reports/a_t2_completion_results.md) giữ done;
actual descriptor-in-prompt/PA vẫn ở P2. [Nền G/E](foundation.md) có CPU/CI,
Modal CPU synthetic lịch sử, chưa real model/GPU. Bằng chứng cũ chỉ lịch sử.

Toàn train input/structure đã từng khảo sát và dùng chọn header rule; holdout
chỉ chưa xem đáp án, không khẳng định unseen domain. Gold không vào inference;
public/private không tuning/training. Dev phát triển, calibration chọn ngưỡng.
Docker P3 sau P2/G2; draft giữ nguyên. Model thật chỉ Modal, không local weights/CUDA.

Plan tuần cũ chỉ tra lịch sử tại
[archive/timeline-20261103](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/tree/archive/timeline-20261103),
không fallback. Không upload dữ liệu/artifact BTC.
Phiên sau G0: `uv run --locked python scripts/harness.py context --task P1`;
đọc read_first/Timeline/task, kiểm split/scorer provenance và gate current.

## Graphify cho Codex — 05/11/2026

Đã setup Graphify local `0.9.102`, tool dependency/lock riêng, skill `$graphify`
và wrapper `scripts/graphify_local.py`; [cách dùng](graphify.md),
[nghiệm thu](../reports/graphify_setup_results.md). Graph current: 49 file Python,
566 node/1921 cạnh; backend tắt, không data/gold/runs/docs/credentials.
Query/explain/path/build/incremental/HTML và synthetic ignore check pass.
Chưa đo tiết kiệm token A/B; không phải model/PA hoặc prerequisite P1.

CPU hiện hành sau tích hợp: **238 passed in 44.39s**, Ruff/format pass, source không đổi;
`runs/cpu-check-20261105T125449495803Z-h34xb6o4/gate.json`. Đã đọc JSON/ba log; context P1 passed/current,
ready, không warnings. Bằng chứng P0 phía trên là lịch sử trước tooling;
CPU này thay record CPU hiện hành, không mở thêm gold hoặc thay acceptance P0.
Backlog ghi development_tooling của P1; trạng thái P1 todo và P2 blocked giữ nguyên.

## Đo token Graphify — 05/11/2026

Đã làm một retrieval replay cho audit `run-eval` xuyên7 file implementation và
4 file test, 12 nhóm source evidence do tác giả review; không phải A/B hai agent
độc lập hoặc billing thực. [Báo cáo](../reports/graphify_token_benchmark.md),
[protocol](research/graphify_token_benchmark.md). `o200k_base` tham chiếu:
graph26716 token, toàn49 file120364, rg-whole-file36703, rg-scoped23807.
Graph giảm77,80%/27,21% so hai mốc đầu, nhưng tăng12,22% so rg-scoped.
Cộng context chung cố định30525 token của snapshot: giảm62,06% so đọc toàn repo.
Hai nhánh scoped đọc cùng22214 source token; graph overhead thêm2909 token.
Kiểm nhạy cl100k_base không đổi dấu kết luận. Không đổi routing/skill chỉ từ
một câu hỏi; dùng kết quả này như case study, không claim tiết kiệm trung bình.

Dependency tokenizer có pyproject/lock riêng trong run ignored; không đổi
runtime DataMate/tool Graphify. Payload/hash/script/counts local trong
`runs/graphify-token-benchmark-20261105/`; corpus/graph không đổi, không mở gold
BTC hoặc gọi model. Backlog chỉ thêm development_tooling evidence của P1;
P1 todo/ready và P2 blocked giữ nguyên.

CPU hiện hành: **238 passed in 79.02s (0:01:19)**, Ruff/format pass, exit0, source không đổi;
`runs/cpu-check-20261105T140812618084Z-82ztxewm/gate.json`. Đã đọc JSON/ba log; context P1
passed/current, ready/no warnings. Không thay acceptance P0 hoặc trạng thái
task; P1 todo/ready, P2 blocked. Chưa có bằng chứng model/PA/B0.
Lệnh kiểm tra: `uv run --locked python scripts/check.py`.
