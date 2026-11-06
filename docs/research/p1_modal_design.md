# P1: Model trên Modal và GPU proxy

Ngày 06/11/2026, giờ Việt Nam. **Người dùng đã duyệt triển khai trực tiếp**;
chưa cho phép coi adapter, GPU hoặc G1 đã hoàn tất.
Tracker duy nhất: `tasks/backlog.json` (P1 in_progress) và
`docs/project_state.md`. Đây là thiết kế cho đúng P1, không phải roadmap mới.

## Mục tiêu và căn cứ

Chứng minh một model hợp lệ chạy thật bằng vLLM trên Modal RTX-PRO-6000
sm_120, xuất JSON theo contract, lặp lại hai lượt và chạy được khi chặn mạng.
Tạo evidence có thể tái kiểm cho G1 trước khi nối pipeline P2.

Nguồn kế hoạch là DOCX hiện hành, SHA-256
`b70f5e852b156c7ff0835eebbdd96ccb71b718fd095fd797b554efe5b1837219`,
§4/P1, §5/D1 và G2. Timeline yêu cầu thử 2–3 model, G1 cần ít nhất một model
đạt. User đã yêu cầu bắt đầu triển khai sau báo cáo trạng thái; cách tổ chức
bên dưới là đề xuất kỹ thuật của tác giả, chưa coi là quyết định người dùng.

Đã đọc context/contract, README, state/backlog, harness và Modal runbook;
Graphify đã cập nhật rồi truy vấn phạm vi cpu_smoke/config. Code hiện có:
`infra/modal_app.py` chỉ CPU synthetic; `SmokeConfig` chỉ nhận fake;
`Submission`/`json_object` kiểm output nghiêm ngặt. Chưa có adapter model thật.

Không mở P2, không sửa `predict.sh` sang model, không làm Docker P3,
không benchmark PA hoặc chọn prompt/ngưỡng theo dev/calibration/holdout.
Không đọc hay upload kit, gold, membership, public/private hoặc artifact BTC.

## Các phương án

1. **Hai pha, weights trong Modal Volume:** staging online trên CPU; inference
   GPU đọc Volume read-only và block_network. Giảm download lặp, kiểm offline
   tách bạch; cần hash manifest và quản lý storage. **Tác giả chọn phương án này.**
2. Weights trong Modal Image: dễ tạo image tự chứa nhưng build/cache chậm khi
   đổi model; phù hợp hơn khi khóa model và đóng gói sau P1.
3. Tải weights trong function GPU trước mỗi probe: ít thành phần hơn nhưng
   không chứng minh cold offline và tính tiền GPU khi download; không chọn.

Giữ Python/uv của DataMate; Modal SDK thuộc group cloud hiện có. GPU runtime
chỉ cài trong Modal Image, không cài torch/vLLM/CUDA hoặc tải weights local.

## Model và runtime

Hai ứng viên đầu (chạy tuần tự, không cùng suy luận hoặc cộng weights):

| Model | Revision đầy đủ | Tổng tensor parameters |
| --- | --- | ---: |
| Qwen/Qwen3-14B | `40c069824f4251a91eefaf281ebe4c544efd3e18` | 14,768,307,200 |
| Qwen/Qwen2.5-Coder-14B-Instruct | `aedcc2d42b622764e023cf882b6652e646b95671` | 14,770,033,664 |

Card/license chính thức là Apache-2.0, dense; ngày công bố weights phải có
nguồn trước 01/10/2026 và được ghi trong manifest trước staging. Không model
phụ/embedding/reranker. Tokenizer và chat template lấy cùng revision.
Pin không được dùng `main`, tag trôi hoặc `trust_remote_code=True`.
Ngày công bố cả họ model không đủ chứng minh snapshot đã ghim: phải có
timestamp commit snapshot trước cutoff hoặc LFS hash từng shard trùng với
snapshot đã chứng minh tồn tại trước cutoff. Thiếu chứng cứ thì không staging.
Metadata HF đã kiểm tại kickoff: snapshot Qwen3 có commit 26/07/2025;
8/8 weight shard và index có lastCommit upload `f8c293defed9c6a8026291e8e7d780697e88d7af`
ngày 28/04/2025. Snapshot Coder có commit 12/01/2025; 6/6 weight shard và
index có lastCommit upload `215507574115bc17fc170a0dc20b86bd7d675d59` ngày
06/11/2024. Đây là chứng cứ history/LFS SHA256 từ HF; download cloud vẫn phải
hash bytes đối chiếu metadata, chưa tự coi weights đã tải/kiểm bytes.

BF16 riêng weights đã khoảng 29.54 GB thập phân (27.51 GiB). Chưa chứng minh
vừa bộ nhớ khi thêm runtime/KV. P1 thống nhất budget **30 GiB** cho vLLM,
ghi đồng thời bytes/GB/GiB để không nhầm đơn vị; đây là cách diễn giải
"~30 GB" trong timeline, vẫn phải kiểm peak thực tế. Không tự đổi sang model
lượng tử hóa hoặc tăng budget nếu OOM; ghi fail rồi xem lại phương án.

GPU selector `RTX-PRO-6000`; NVIDIA ghi compute capability 12.0.
Runtime dự kiến vLLM 0.11.1, torch 2.9.0, CUDA 12.8 theo source/tag chính thức;
khóa base image digest và bộ packages trong cloud lock trước build. Đây là
ứng viên runtime đã có source hỗ trợ build sm_120, **chưa được kiểm kernel thật**.
Không trộn API từ stable mới với version ghim. Version mới hơn chỉ thay nếu
có lý do/nguồn và cập nhật research trước job.
Chọn v0.11.1 vì hai decoder Qwen2/Qwen3 đã có hỗ trợ, Python 3.11 tương thích
project và không cần kernel Qwen3.5 ở P1. Source/tag mới hơn đã khảo sát có
khác biệt CUDA giữa tài liệu và Docker build; không chọn chỉ vì mới hơn.
Cloud dùng `infra/p1_runtime/pyproject.toml` + `uv.lock` riêng, khóa Linux
x86_64/Python 3.11, vLLM 0.11.1/torch 2.9.0 và index cu128. Chỉ resolve lock
local; chỉ sync/install trong Modal. Base CUDA 12.8.1-devel Ubuntu22.04 phải
resolve OCI digest trước build. Runtime thật phải báo đúng tuple/version.

## Ranh giới thành phần và luồng

`preflight local → staging CPU online → Volume đã kiểm hash →
inference GPU offline → validate/evidence local`.

- `src/datamate/model_probe.py`: logic CPU nhẹ để kiểm manifest/config,
  dựng fixture/prompt synthetic và tổng hợp kết quả. Không import Modal,
  torch, vLLM hoặc tự kết nối mạng khi import.
- `infra/modal_model_probe.py`: Image/Volume và entrypoint cloud; import SDK
  chỉ trong infra. Local preflight phải chạy trước remote launch thực tế,
  kể cả trước khi khởi tạo App/Image có thể tạo side effect.
- `scripts/p1_probe.py`: entrypoint local kiểm account/budget/pin rồi gọi
  Modal theo hai pha rõ ràng. Không dùng `modal run` như đường bỏ qua guard.
- `configs/p1_probe.yaml`: model order, seed, limits và budget. Không thay
  cấu hình CPU smoke cũ để giả làm model probe.
- `infra/p1_runtime/pyproject.toml` và `uv.lock`: dependency GPU tách biệt;
  không thêm torch/vLLM vào group local hoặc sync GPU environment trên máy này.
- `manifests/models.json`: chỉ ghi model đã verify eligibility; execution
  pass/fail nằm trong run/report, không suy ra từ eligibility=true.
- `tests/unit/test_model_probe.py`, `tests/integration/test_model_probe.py`:
  CPU synthetic và fake transport, không thu thập model/cloud lúc import.

Builder có thể điều chỉnh tên helper/private function theo codebase; các
ranh giới policy, gate và dữ liệu trong tài liệu này phải giữ nguyên.

### Preflight, chi phí và dữ liệu

Xác minh live `MODAL_PROFILE=vuonghungnguyen07`, token workspace/user đúng
`vuonghungnguyen07`; không đổi active profile toàn máy, không lưu token ID/secret
trong source hoặc evidence. Lệnh account đã được kiểm read-only ở kickoff.
Trước job phải kiểm lại billing/usage và app đang chạy; chưa đọc số dư/usage
thì không ghi đã đủ tiền. Budget cấu hình 30 USD là mức được phép, không phải
hard billing cap.

Giới hạn một container, min/buffer=0, retries=0; chạy tuần tự hai model.
GPU function timeout 1,200s, startup timeout 1,200s; staging CPU timeout
3,600s, startup timeout 600s, không cấp GPU khi download. Theo giá nguồn
06/11/2026, GPU $0.000842/s (~$3.0312/h); tổng hai GPU runs nếu mỗi run tính
cả startup+execution 2,400s là ~$4.04, chưa CPU/build/storage/thuế. Dự toán
phải tính các khoản này và được kiểm trước launch; không launch nếu dự toán
vượt 30 USD hoặc billing/usage chưa xác minh. Timeout không là billing cap.

Không tự retry run bị mất kết nối; tra app/run ID trước. Ghi ID để stop đúng
app khi lỗi. Volume giữ weights để P2 tái dùng, ghi dung lượng/chi phí lưu
trữ tiếp diễn; không xóa Volume như cleanup mặc định. Nếu không đủ hạn mức
cho cả hai ứng viên, báo phần chưa chạy; không ghi G1 hoàn tất toàn P1.

Chỉ copy allowlist code/config và fixture synthetic mới; không copy root,
data, runs, credentials hoặc `.venv`. Staging chỉ tải file của revision
được phép từ model public. Ghi SHA-256 weights/tokenizer/config/chat template,
kiểm thiếu file/hash trước inference. Không chạy code Python từ model repo.

### Inference và bộ nhớ

Load model từ đường dẫn snapshot local trong Volume read-only.
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, tắt telemetry; function có
`block_network=True`, probe outbound phải fail. Hỏng/mất weights phải fail,
không fallback tải mạng hoặc revision khác. Ghi Image ID/digest, lock hash,
model/artifact hashes và hardware/runtime/version thực đo.

BF16, context tối đa 2,048 token, max_num_seqs=1, max_tokens=256;
temperature=0, seed=0, fixed prompt order, một request mỗi lần. Qwen3 tắt
thinking trong chat template; Qwen2.5 không nhận option Qwen3. Apply đúng
tokenizer chat template thay vì nối chat token thủ công.
`enforce_eager=True` để tránh overhead CUDA graph trong probe; tắt prefix
caching. Cache biên dịch chỉ được ghi ngoài mount weights.

`gpu_memory_utilization = 30*1024**3 / total_device_bytes`; không dùng
`kv_cache_memory_bytes` thay cho total budget (nó chỉ giới hạn KV và bỏ qua
utilization). Đo peak allocated/reserved và peak process GPU memory có thể
lấy được; lưu cách đo, sampling và giới hạn phép đo. Từ chối claim budget
pass nếu thiếu đo hoặc vượt 30 GiB. RTX-PRO-6000 không mô phỏng throughput
hay số GPU của máy chấm; chỉ là proxy kiến trúc/kernel và budget bộ nhớ.

Batch-invariant là thử nghiệm riêng nếu version hỗ trợ/nguồn xác nhận, không
bật bằng giả định. Hai lượt trùng chỉ chứng minh cấu hình/fixture đã chạy,
không cam kết mọi batch/GPU/model đều tất định.

### Fixture, output và G1

50 câu synthetic tự chứa, tiếng Anh/Việt, phủ 9 output type, leading zero,
unicode, tháng/ngày, percent, list/table. Expected viết tay tách khỏi payload
gửi model; ID chỉ để correlation, không chọn đáp án hoặc prompt theo ID.
Không dùng fixture fake trả sẵn làm evidence của model thật.

Structured output dùng JSON schema phù hợp API version ghim; không chấp nhận
code fence, duplicate keys, NaN/Infinity hoặc extra keys. Kiểm thêm bằng
`json_object` và `Submission`, expected ID và type/value. Chỉ canonicalize
để so kết quả bằng `Submission.output()`, không repair nội dung lỗi.
API v0.11.1 là `SamplingParams(structured_outputs=StructuredOutputsParams(json=schema))`.

Mỗi model chạy **hai lượt độc lập cùng 50 câu**, cùng Image/config/seed/order;
lưu raw output và normalized output riêng. Mỗi lượt cần 50/50 output hợp lệ:
≥99% trên 50 câu có nghĩa phải đủ 50. So equality normalized 50/50 giữa hai
lượt; raw/token equality báo thêm. Báo synthetic correctness riêng và phải có
ít nhất một non-abstain output đúng ở mỗi type có answer. All-abstain không
đủ nghiệm thu. Không gọi synthetic correctness là PA, B0 hoặc chất lượng BTC.

"Độc lập" ở đây là **hai OS subprocess/LLM engine mới**, chạy tuần tự trong
cùng GPU container để giữ cùng hardware. Không tái dùng engine/prefix cache;
process lượt trước phải thoát và worker/GPU allocation được thu hồi trước
lượt sau. Ghi PID/engine start, exit code và xác nhận cleanup. Filesystem cache
biên dịch có thể giữ; đây không phải hai cold container hoặc phép đo cold start.
Mỗi model vẫn dùng một container run, timeout gồm hai lần load/generate.

G1 cần ít nhất một model đạt eligibility + sm_120 + memory + offline + valid
JSON + repeatability. Scope D1 thử hai ứng viên; ghi kết quả từng model,
không giấu failed run hoặc suy đoán model chưa chạy. Model pass sẽ dùng để
bắt đầu P2, không chọn "model tốt nhất" chỉ bằng smoke này.

Artifact dưới `runs/p1-probe-<timestamp>-<id>/`, không ghi đè run cũ:
preflight (không token), source/config/image/model hashes, runtime/hardware,
memory/cost estimates, outbound probe, raw/normalized per-round outputs,
counts/failures/diffs/timings, app/run IDs và acceptance.json. Không có BTC.

## Kiểm chứng, rủi ro và việc còn phải làm

TDD cho guard và tổng hợp kết quả: sai account/budget/revision phải chặn trước
remote; thiếu weights/hash/network/memory phải fail; malformed/duplicate/missing
output và hai lượt lệch không thể pass. Mock transport chỉ chứng minh CPU,
không điền GPU/model success. Giữ toàn bộ test cũ và CPU gate chuẩn.

Sau implementation: chạy CPU gate, đọc gate.json và ba log; test import không
gọi SDK/cloud. Sau remote: đọc full evidence, billing thực có thì ghi, chưa có
thì ghi chưa có; cập nhật state/backlog. P1 chưa done trước đủ acceptance.

Rủi ro cần phép thử thật: BF16 chật budget, sm_120 kernel, guided JSON với
type union, repeatability và thời gian load. Lỗi phải được ghi nguyên nhân
trước retry/đổi config; không đổi expected hoặc giảm gate để pass.

## Nguồn chính thức

- [Modal GPU selector](https://modal.com/docs/guide/gpu)
- [Modal pricing](https://modal.com/pricing)
- [NVIDIA CUDA GPUs](https://developer.nvidia.com/cuda-gpus)
- [Modal Volumes](https://modal.com/docs/guide/volumes)
- [Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B)
- [Qwen2.5-Coder-14B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct)
- [Qwen3 công bố 29/04/2025](https://qwenlm.github.io/blog/qwen3/)
- [Qwen2.5-Coder công bố 12/11/2024](https://qwenlm.github.io/blog/qwen2.5-coder-family/)
- [Qwen3 snapshot metadata](https://huggingface.co/api/models/Qwen/Qwen3-14B/revision/40c069824f4251a91eefaf281ebe4c544efd3e18)
- [Coder snapshot metadata](https://huggingface.co/api/models/Qwen/Qwen2.5-Coder-14B-Instruct/revision/aedcc2d42b622764e023cf882b6652e646b95671)
- [Qwen3 pinned tree/LFS history](https://huggingface.co/api/models/Qwen/Qwen3-14B/tree/40c069824f4251a91eefaf281ebe4c544efd3e18?recursive=true&expand=true)
- [Coder pinned tree/LFS history](https://huggingface.co/api/models/Qwen/Qwen2.5-Coder-14B-Instruct/tree/aedcc2d42b622764e023cf882b6652e646b95671?recursive=true&expand=true)
- [vLLM 0.11.1 GPU installation](https://docs.vllm.ai/en/v0.11.1/getting_started/installation/gpu.html)
- [vLLM 0.11.1 CUDA requirements](https://github.com/vllm-project/vllm/blob/v0.11.1/requirements/cuda.txt)
- [vLLM 0.11.1 build architectures](https://github.com/vllm-project/vllm/blob/v0.11.1/CMakeLists.txt)
- [vLLM 0.11.1 structured output API](https://docs.vllm.ai/en/v0.11.1/features/structured_outputs/)

Pin/source đầy đủ và ngày công bố phải được đối chiếu lần cuối trước manifest
và staging; nguồn mô tả khả năng hỗ trợ không thay evidence chạy thật.

## Quyết định thực thi sau review — 06/11/2026

Người dùng đã duyệt thiết kế và triển khai trực tiếp; đã xác nhận credit/hạn
mức khả dụng ít nhất30USD. Chỉ ghi là xác nhận người dùng, không là hard cap.

Modal1.6.3 chỉ nhận `add_python=3.11` ở Image.from_registry; uv trong Image
cài interpreter chính xác3.11.18 rồi sync cloud lock bằng interpreter đó.
Worker phải báo đúng Python3.11.18 cùng tuple vLLM/torch/CUDA. Không cài local.

Ngoài Volume weights read-only, có Volume evidence nhỏ chỉ chứa synthetic
(`datamate-p1-probe-evidence-v1`): checkpoint atomic và commit mỗi lượt trước
khi bắt đầu lượt sau. events local lưu UUID evidence và appID, kể cả lỗi khi
vào app.run/build. Volume này có chi phí lưu trữ nhỏ tiếp diễn, không chứa BTC.
Đây là lựa chọn thực thi để giữ kết quả khi disconnect/OOM, không mở thêm pha.

Function GPU dùng deadline monotonic chung tính cả hash/load/round/cleanup và
chừa90s trả kết quả. Mỗi lượt phải có sample NVML và peak Torch allocated/
reserved hợp lệ; bất kỳ peak nào vượt30GiB đều fail, aggregate không che lượt
thiếu evidence. Diagnostic được lọc credential và query URL trước lưu.

## Phép thử Qwen3 đầu và sửa conformance — 06/11/2026

Run `runs/p1-probe-20261106T073938Z-fcc48667/` thực sự chạy hai engine trên
RTX-PRO-6000 sm_120, Python3.11.18/vLLM0.11.1/torch2.9.0+cu128/CUDA12.8.
Mỗi lượt50record,47record qua Submission, normalized outputs trùng. Ba record
sai: table answer là array; unanswerable và abstain có answer chuỗi.
Schema cũ chỉ anyOf các dạng answer mà không gắn discriminator type; đó là
lỗi conformance của decoder schema, không đổi expected hoặc nới scorer.

Peak NVML cả hai lượt30.822265625GiB; Torch reserved30.076171875GiB.
vLLM target30GiB chưa tính đủ overhead đo được. Quyết định trước thử lại:
engine target29GiB, reserve1GiB trong tổng30GiB; giữ BF16/context2048, không
tăng trần hay đổi quant/model. KV log trước sửa còn2.12GiB cho max2048token,
nên giảm1GiB vẫn có headroom KV theo phép đo; fit thật phải đo lại.

Decoder chuyển sang union các object có type const và answer tương ứng với
Submission, đặc biệt table object và abstain/unanswerable null/absent.
Regression dùng validator JSON Schema CPU tái hiện cả ba giá trị sai, không
đọc gold. Thử mới phải đạt50/50 từng lượt, hai engine mới và mọi peak<=30GiB;
run fail ban đầu được giữ nguyên. Đây không phải chọn/tuning bằng BTC.
