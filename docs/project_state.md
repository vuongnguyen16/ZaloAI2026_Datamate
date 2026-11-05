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

## Source đã xuất bản — 05/11/2026

Đã đẩy 45 file code/config/tài liệu và test synthetic lên `main` tại
[02bac28](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/commit/02bac28d4c324f647841e04a0cd97c9a3ab9184a):
P0 split/scorer/scoped reader/evaluation/bootstrap/taxonomy và Graphify local.
[GitHub CPU gate](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/actions/runs/42043205165)
success, **238 passed in 9.83s** trên Ubuntu; Ruff/format pass. Đã đọc job
steps và log. Các câu chưa commit/push trong phần nghiệm thu trước mô tả
thời điểm triển khai ban đầu; source hiện đã xuất bản theo commit trên.

Kit, gold, membership, artifact BTC, runs, graph/cache, môi trường và credentials
tiếp tục local/ignored. Review publication do tác giả thực hiện; chỉ provenance
pointer/aggregate và fixture synthetic đi cùng source. CPU local phía trên
vẫn passed/current; việc xuất bản không đổi acceptance P0 hoặc trạng thái P1/P2,
không có model/Modal/B0/PA quality claim mới. Bước tiếp theo vẫn là P1 theo
`uv run --locked python scripts/harness.py context --task P1`.


## Superpowers cho phát triển — 05/11/2026

Đã cài Superpowers **7.0.2**, ghim `22f0b463e7a5e579904dd6211a520321035526f7`,
15 skill gốc/80 file trong `.agents/skills/superpowers/`, MIT/provenance đi kèm.
[Cách dùng](superpowers.md), [nghiệm thu](../reports/superpowers_setup_results.md),
[quyết định](research/superpowers_setup.md). Native registry Codex nhận15/15
enabled,0error; 80blob khớp source,12script syntax pass, sdd-workspace synthetic
exit0. Chỉ initialize/initialized/skills/list, không gọi model hoặc mở thread.

AGENTS bootstrap using-superpowers trước coding; tên local gọi trực tiếp như
$brainstorming/$systematic-debugging. Thư viện repo-scoped, không plugin global;
không nhúng toàn bộ body vào context. Giữ datamate-increment/Graphify, timeline,
state/backlog và scoped data. Spec/plan ở docs/research/ cho task hiện hành.
Dependency/runtime/uv.lock giữ nguyên; pyproject chỉ thêm Ruff exclusion cho
vendor để không sửa ví dụ trong tài liệu upstream. Gate đầu format fail đã
ghi ở report, không bỏ first-party test hoặc đổi expected.69hash source/config/
test/lock và hai skill cũ khớp baseline. Không kit/gold/Modal job, không PA/B0.

CPU hiện hành: **238 passed in 124.97s (0:02:04)**, Ruff/format pass, exit0, source không đổi;
`runs/cpu-check-20261105T145024412015Z-vo2acxq5/gate.json`. Đã đọc JSON/ba log, context P1
passed/current, ready/no warnings. Backlog chỉ thêm development_tooling;
P1 todo/ready, P2 blocked giữ nguyên. Self-review, không reviewer độc lập.
Chưa đánh giá chất lượng coding/token savings của LLM bằng Superpowers.
Skill dùng được từ lượt tiếp theo; optional visual companion chưa chạy.

## Archify cho onboarding — 05/11/2026

Đã cài Archify **3.2.0**, ghim `208acba8d412335185b2056fedf54b3405df43fb`,
skill workspace `.agents/skills/archify/`; [cách dùng/prompt](archify.md),
[nghiệm thu](../reports/archify_setup_results.md),
[scope](research/archify_setup.md). 203/203 blob upstream khớp, MIT/notices
giữ nguyên. Native Codex registry nhận archify enabled, 0 load error; doctor
pass; demo synthetic finalize đủ validate/deliver/check/browser-check pass
trên Chrome có sẵn. Chưa review cảm nhận hình ảnh hoặc vẽ kiến trúc DataMate.

Output/receipt trong `.archify/` local/ignored; AGENTS yêu cầu tắt update check
và dùng source evidence sau context/Graphify. Có prompt onboarding tiếng Việt,
phân biệt code đã có với kế hoạch. Không sửa runtime/lock hoặc config global;
110 file baseline runtime/config/test/lock giữ nguyên. Không đọc kit/gold hoặc
artifact BTC, không model/Modal/PA/B0. Giữ các thay đổi Superpowers có sẵn.
Backlog chỉ thêm development_tooling của P1; P1 todo, không mở thêm task.

CPU hiện hành sau setup Archify: **238 passed in 93.84s (0:01:33)**,
Ruff lint/format pass, exit0;
`runs/cpu-check-20261105T150151673404Z-bkz19z94/gate.json`. Đã đọc JSON/ba log;
context P1 passed/current, ready, không planning error/warning. Timeline check
current. P0/G0 done, P1 todo/ready, P2 blocked; không commit/push trong phiên.
Skill dùng từ lượt tiếp theo; catalog chưa hiện thì mở lại phiên workspace.

## Trang onboarding DataMate — 05/11/2026

Đã tạo [trang onboarding tiếng Việt local](../.archify/explainer-datamate-onboarding-20261105-220839/datamate-onboarding.html)
cho đồng nghiệp mới: bài toán/contract, luồng ingest/profile đã có, evaluator
scoped, sơ đồ kiến trúc mục tiêu và thứ tự đọc code. Phân biệt A-T1/A-T2/P0
đã hoàn thành với model/pipeline P1–P9 còn kế hoạch; không tạo module hoặc job.
23 source range kiểm tại `fce24e8579cb852ea7add3459c92a90d459aab56`;
README trích committed bytes vì working tree có chèn tài liệu tooling. Trang
ghi rõ các path dirty và nguồn ghim; không coi thay đổi local là source HEAD.

Archify finalize explainer cuối: validate/deliver/check/browser-check pass,
0 warning; receipt trong `.archify/explainer-datamate-onboarding-20261105-220839/review-2/`,
audit nguồn `source-audit.json` cùng thư mục artifact. Lượt đầu browser fail
vì chữ sơ đồ nhỏ; đã gộp cache vào bước nạp và verifier/formatter vào bước
chốt đáp án, giữ chi tiết trong lời dẫn. Không đổi renderer hoặc ngưỡng kiểm.
Chỉ kiểm tự động, chưa review cảm nhận hình ảnh; nút Viewer dùng English fallback.
Artifact/draft/evidence local/ignored, không đọc kit/gold hoặc chạy evaluation.
Runtime/backlog/status không đổi; CPU hiện hành vẫn là gate Archify setup ở trên.

## Archify chỉ dùng Anh/Việt — 05/11/2026

Theo phản hồi người dùng, đã sửa skill/default explainer: nội dung chỉ tiếng
Anh hoặc Việt theo yêu cầu, UI cố định tiếng Anh. Renderer trước đây thiếu
locale thì chọn `zh-CN`; đã đổi fallback thành `en`, đồng thời yêu cầu
`meta.locale=en` trong mọi draft. Bỏ câu mẫu tiếng Trung trong SKILL và các
hướng dẫn authoring chính. [Kết quả](../reports/archify_language_results.md).

Hai test render HTML thật từ draft Anh/Việt thiếu locale: trước sửa 2 fail
đúng lỗi, sau sửa 2 pass. Quick skill validation, doctor/syntax pass. Trang
onboarding đã được tạo lại ở cùng đường dẫn; finalize đủ bốn gate pass.
12 body-text sample từ browser và 47 menu-word field không có chữ Trung.
Chỉ kiểm tự động, chưa review cảm nhận hình ảnh.

Provenance hiện hành ghi rõ 4 file upstream sửa local, 1 test thêm; 199 file
khác nguyên hash, license/notices giữ nguyên. Phải giữ/áp lại patch khi nâng
cấp. Hướng dẫn tuyên bố upstream nguyên bản phía trên là lịch sử setup.
Backlog chỉ cập nhật development_tooling, P1 vẫn todo; không code DataMate,
gold/kit, job model/Modal hoặc PA/B0 mới.

CPU hiện hành: **238 passed in 127.90s (0:02:07)**, Ruff lint/format pass,
exit0; `runs/cpu-check-20261105T152236134716Z-x5pxobyq/gate.json`. Đã đọc JSON
và ba log, source không đổi trong gate; context P1 passed/current, ready/no
warnings. Test Node ngôn ngữ 2/2 pass chạy riêng. Không commit/push.

## Sơ đồ runtime hiện có — 05/11/2026

Đã tạo [HTML kiến trúc runtime tổng quan](../.archify/architecture-datamate-runtime-20261105-224342/datamate-runtime.html)
cho đồng nghiệp mới: luồng CLI/predict → format stub → JSONL/log, nhánh
loader/profiler và evaluator/scoped reader riêng. Phụ thuộc Modal CPU synthetic,
ranh giới account cloud và policy gold được giải thích trong card; không coi
actor policy là xác thực danh tính hoặc guard ứng dụng là OS ACL. Phần model,
domain_lib và Docker được ghi rõ là kế hoạch P1/P2/P3.

Source ghim `fce24e8579cb852ea7add3459c92a90d459aab56`; 20 range hợp lệ,
README đối chiếu committed bytes vì working tree dirty. Danh sách path local
có ở source-scope.md cạnh artifact. Archify finalize architecture đủ
validate/deliver/check/browser-check pass, không diagnostic; audit nhãn/tiêu đề
tiếng Việt hiện diện trong HTML và không có Han trong authored candidate.
Chỉ kiểm tự động, chưa review cảm nhận hình ảnh. Receipt/audit local cùng folder.

Không sửa runtime/config/skill/backlog, không mở data/gold/membership/artifact BTC,
không gọi model/cloud hoặc publish. P0/G0 done, P1 todo/ready và P2 blocked giữ
nguyên; timeline check current, context CPU passed/current/no warnings trước
khi tạo artifact. Không chạy lại CPU gate vì chỉ thêm HTML ignored và handoff
tài liệu; gate hiện hành vẫn là record language-patch phía trên.

## Xác minh trước cập nhật GitHub — 05/11/2026

Theo yêu cầu người dùng, chuẩn bị xuất bản 301 file tooling/config/tài liệu:
Superpowers 7.0.2, Archify 3.2.0 cùng patch Anh/Việt, hướng dẫn và báo cáo.
Hash provenance khớp 204 file Archify (gồm test thêm) và 81 file Superpowers
(gồm license); giữ executable bit của 10 script upstream. Rà soát publication
do tác giả thực hiện; không phát hiện mẫu credential, tài liệu first-party
UTF-8/NFC hợp lệ. Kit/gold/membership/runs/cache và HTML DataMate trong
`.archify/` tiếp tục local/ignored; các HTML đi kèm vendor là ví dụ upstream.

Kiểm tra mới: `uv run --locked python scripts/timeline.py check` current;
`node --test .agents/skills/archify/tests/language-default.test.mjs` 2/2 pass;
`uv run --locked python scripts/check.py` exit0, **238 passed in 139.38s**,
Ruff lint/format pass, source không đổi trong gate. Đã đọc gate.json và ba log:
`runs/cpu-check-20261105T160330296462Z-mdbwuv9t/gate.json`.
Bản ghi này mô tả kiểm tra local trước push; CI GitHub kiểm riêng sau push.
Các câu chưa commit/push ở phần trước là lịch sử các phiên triển khai.
P0/G0 done, P1 todo/ready, P2 blocked; không có model/Modal/PA/B0 mới.
