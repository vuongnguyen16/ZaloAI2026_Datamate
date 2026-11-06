# P1: model/runtime trên Modal — 06/11/2026

**P1/G1 đã đạt với cả hai ứng viên.** P2 là bước tiếp theo; chưa mở task P2.
Đây là bằng chứng runtime/format synthetic, không phải B0
hoặc PA dữ liệu BTC.

Thiết kế đã được người dùng duyệt triển khai trực tiếp:
[design](../docs/research/p1_modal_design.md), [plan](../docs/research/p1_modal_plan.md).
Profile/workspace/user `vuonghungnguyen07` xác minh live trước từng launch;
credit/hạn mức>=30USD do người dùng xác nhận lúc06:53:37UTC. Trần30USD không
phải hard billing cap.

## Model và cổng Modal

| Ứng viên | JSON hợp lệ (lượt1/lượt2) | Raw text/token lặp | Peak NVML | G1 |
| --- | --- | --- | --- | --- |
| Qwen3-14B | 50/50,50/50 | 50/50,50/50 | 32,003,588,096bytes (~29.81GiB) | pass |
| Qwen2.5-Coder-14B-Instruct | 50/50,50/50 | 50/50,50/50 | 31,932,284,928bytes (~29.74GiB) | pass |

Qwen3 revision `40c069824f4251a91eefaf281ebe4c544efd3e18`,
14,768,307,200 parameters; Coder revision
`aedcc2d42b622764e023cf882b6652e646b95671`,14,770,033,664 parameters.
Apache-2.0, exact snapshot/shard history trước01/10/2026. Model chạy tuần tự,
không cộng hai model làm pipeline inference hoặc thêm auxiliary model.

Runtime thật đã quan sát ở Qwen3: RTX PRO 6000 Blackwell Server Edition,
compute capability12.0, total102,016,548,864bytes;
Python3.11.18/vLLM0.11.1/torch2.9.0+cu128/CUDA12.8, base toolkit12.8.1.
OCI digest `sha256:6617a625f4090c76c545a0e7d63f2e441718ef9af7f4efe7dd1242a29e289fd7`;
cloud package versions/hashes khóa riêng trong infra/p1_runtime/uv.lock.

30GiB là trần nghiệm thu đo; vLLM target29GiB, reserve1GiB overhead sau phép
đo. BF16/context2048/max_num_seqs1/max_tokens256, eager, seed0/temp0,
Qwen3 non-thinking; không batch-invariant hoặc quantization. Đây không phải
physical GPU partition hoặc throughput proof trên2×RTX5090.

50 prompt tự chứa Anh/Việt phủ9type; expected chỉ local, không gửi model.
Hai engine OS process mới trong cùng GPU container, không engine/prefix cache
dùng chung; filesystem kernel cache có thể warm. Qwen3 PID23/3160, exit0 và
cleanup pass; durations105.65s/43.76s (không tính toàn bộ startup/hash/commit).
Torch peak allocated31,073,122,816bytes/reserved31,203,524,608bytes mỗi lượt;
NVML samples1488/603. Cả hai lượt có đầy đủ memory evidence dưới30GiB.

Coder cùng runtime/hardware và hai PID23/3948, durations138.16s/53.37s;
Torch allocated31,093,361,152/reserved31,132,221,440bytes, NVML samples1882/716.
Non-abstain synthetic40/40 mỗi lượt; raw text/token IDs trùng50/50.
Không dùng khác biệt này làm quality ranking. Giữ Qwen3 làm primary theo
thiết kế ban đầu,14,768,307,200 tổng parameters; Coder là candidate đã kiểm,
không cùng tham gia pipeline inference. Registry ghi rõ predict còn stub/P2.

Qwen3 normalized/raw text/token IDs đều trùng50/50. JSON validity100% không
đồng nghĩa accuracy100%: correct non-abstain synthetic38/40 mỗi lượt, hai lỗi
boolean còn lại; không dùng đây để chọn model tốt nhất hoặc claim PA.
Offline outbound probe fail như yêu cầu, weights write probe bị chặn;
hash snapshot khớp, block_network/read-only và runtime pins pass.

## Run và các lần fail được giữ lại

| Run | App | Kết quả |
| --- | --- | --- |
| `p1-probe-20261106T073327Z-5dc4f6c9` | `ap-VSsxbmehfJDjuJnwF1yN0s` | startup Image build fail do registry mặc định khác lock; chưa staging/GPU inference |
| `p1-probe-20261106T073938Z-fcc48667` | `ap-txhGTKrnI3gTjgrA70zoM6` | model thật2×50,47valid/lượt,peak30.822GiB; G1 fail |
| `p1-probe-20261106T080821Z-b4015cd9` | `ap-8MzBpOmzpUkOd4o5pzlfw9` | Qwen3 pass đầy đủ G1, source không đổi trong run |
| `p1-probe-20261106T081654Z-53376f43` | `ap-JrcosZOQwP51IliWGSAUoM` | Coder pass đầy đủ G1, source không đổi trong run |

Mỗi run có preflight/config/model/source hash, events/app IDs, raw result,
acceptance và inspection summary local/ignored. Weights chỉ trên Modal Volume
`datamate-p1-model-weights-v1`; evidence synthetic có Volume riêng
`datamate-p1-probe-evidence-v1` và UUID trong events. Không có kit/gold/BTC.
Failed run không bị ghi đè hoặc dùng green cũ để che lỗi mới.

Registry issue được tái hiện bằng offline lock check: mirror exit1, đúng
PyPI exit0. Đã ghim UV_INDEX_URL/UV_DEFAULT_INDEX, giữ lock nguyên vẹn.
Live conformance failure được tái hiện bằng JSON Schema validator: schema cũ
cho table trả array và abstain/unanswerable trả string. Decoder typed union
đã sửa đúng contract; không sửa fixture expected hoặc giảm gate. Memory target
giảm trong trần, không tăng budget hoặc đổi model/quant. Mỗi fix RED→GREEN.

## CPU và review

CPU cuối trên `main` sau merge local: **314 passed, 1 skipped in 70.79s**,
Ruff lint/format pass, exit0, source không đổi trong gate;
`runs/cpu-check-20261106T094846717921Z-mpg559ct/gate.json`.
Đã đọc gate.json và ba log. Skip duy nhất: Windows không có quyền tạo symlink
cho fixture, test giữ nguyên và có thể chạy trên môi trường hỗ trợ.
CPU không import GPU/SDK khi collection; local không cài torch/vLLM/weights.
Dev JSON Schema dependency được thêm bằng uv/lock, không pip tùy tiện.

Graphify update khi bàn giao đã phát hiện TOML cloud bị extractor nhận làm
source; guard Python-only chặn đúng. Đã thêm TOML/lock vào ignore trước
extraction, giữ nguyên guard; graph bị từ chối được giữ ở scratch trước khi
tái tạo. Update/status current:705nodes,2294edges,63Python source files.

Review độc lập source-only phát hiện5Important,0Critical,0Minor: Image API
Python selector, duplicate app state, memory từng lượt, deadline/checkpoint,
startup diagnostics. Cả5 đã có regression RED→GREEN; toàn suite sau sửa
312pass/1skip. Không re-review sau fix theo workflow inline; GPU experiment
giải quyết phần kernel/memory/runtime reviewer chưa thể kết luận bằng CPU.

Các quyết định của tác giả, theo thứ tự trong ledger:

1. Triển khai plan từ design đã duyệt, không mở vòng duyệt lại cùng phạm vi.
   Nếu diễn giải sai, chi phí là sửa lại implementation.
2. Thêm Volume evidence synthetic riêng để giữ partial round khi disconnect;
   weights vẫn read-only. Chi phí là storage nhỏ được giữ lại.
3. SDK chọn Python series3.11; uv cài chính xác3.11.18 vì SDK không nhận micro.
   Chi phí là thêm lớp interpreter trong cloud image.
4. Kernel/load/memory/correctness phải kiểm thật trên Modal; hai probe đã qua
   cấu hình này. Nếu ngoại suy sang workload khác sẽ có rủi ro tương thích/OOM.
5. Reviewer không fetch lại metadata model/OCI; tác giả đã đối chiếu nguồn và
   digest ở kickoff, staging kiểm hash. Sai provenance sẽ cần làm lại eligibility.
6. Transport nội bộ không là entrypoint hỗ trợ; CLI guarded là đường launch.
   Bypass CLI có thể bỏ guard, đây không phải bảo đảm security/OS ACL.

Không có Minor hoãn lại. Fix live registry, typed union và reserve memory
đều được ghi ở trên cùng bằng chứng RED→GREEN.

## Ngân sách và giới hạn

Theo [giá Modal đã đọc06/11/2026](https://modal.com/pricing), GPU RTX-PRO-6000
$0.000842/s; CPU $0.0000131/core/s, RAM $0.00000222/GiB/s. GPU+8core+64GiB
~$3.919968/h. Dự toán khai báo10USD trong trần30USD, có giới hạn startup/run,
1container,min/buffer0,retries0; mọi retry ở trên sau chẩn đoán/sửa nguyên nhân,
không automatic resubmit. Invoice/billing thực chưa đọc được qua công cụ,
không ghi0USD hoặc suy rằng timeout là hard cap.

Riêng khoảng wall call GPU của hai run pass (gồm queue/startup/hash/stop/network)
177.65s/570.59s, theo rate GPU+8core+64GiB ~0.1934/0.6213USD. Đây là ước tính
compute từ khoảng thời gian, không invoice; chưa gồm failed trial, staging,
build/storage. Provenance và các hash nằm trong `manifests/models.json#/p1_evidence`.
Trước đăng ký model, đã kiểm toàn bộ source hash/candidate input của hai run
khớp tree hiện tại; models.json sau đó chỉ thay bookkeeping/selection/provenance.

Volume giá niêm yết $0.09/GiB/tháng, gồm1TiB/tháng free; quota đã dùng của
workspace chưa xác minh nên không claim storage miễn phí thực tế. Hai snapshot
BF16 khoảng55GiB nếu giữ cả hai; chi phí tiếp diễn cần xem dashboard/quota.
Weights giữ để tái dùng P2, không tự xóa như cleanup. App completed phải được
kiểm trước kết luận không còn container của thí nghiệm chạy.

Chưa chạy PA dev/calibration/holdout, chưa B0, chưa inference pipeline/predict
thật hoặc Docker P3. Holdout/membership và dữ liệu BTC tiếp tục local/kín.
State/backlog đã chốt P1 done, P2 todo/ready; context P2 có CPU passed/current,
không task active, warning hoặc planning error. Timeline check current.
Người dùng chọn merge local ngày06/11/2026. Đã pull main bằng ff-only
(remote không đổi), fast-forward `main` từ7371bf6 tới3f03996 và kiểm lại
toàn cổng CPU trên cây sạch. Nhánh P1 được dọn sau khi test pass;
workspace chính được giữ nguyên. P1 chưa push lên GitHub.

Cả hai app pass đã completed và CLI live check không có app P1 xung đột lúc
08:34:32UTC. Runtime có cảnh báo nanobind lúc shutdown (Qwen3 đã kiểm), nhưng
process exit0/cleanup pass; log giữ nguyên. Không suy ra không có leak khi
chạy lâu; P2/P3 cần đo trên workload thực. Không có GPU job còn giữ theo thiết kế
min/buffer0 và app.run đã kết thúc. Volume vẫn giữ weights/evidence.
