# P2b: context và throughput dev thật

Ngày07/11/2026. Runtime PR#3 đã merge vào main `2f1dbb2` trước khi bắt đầu
khảo sát CPU. Source probe đã review độc lập tại `7396c84`; không sửa source
trong lúc chạy cloud. P2/G2 vẫn chưa hoàn tất; chưa domain_lib/PA/B0.

## Kết luận đo được

- BF16/TP1, context4096 chạy được với đúng cấu hình dưới đây:24/24 JSON hợp lệ,
 4 prompt unique,2lượt ở batch1/2/4; sampled peak 29.833GiB.
- Context8192 + prefill-token-budget8192 không khởi tạo được: KV cần1,25GiB,
 chỉ có0,29GiB. Worker exit1, không timeout, process group đã dọn. Đây là
 bằng chứng thất bại của cấu hình, không phải giới hạn vật lý8k của model.
- Batch4 chỉ nhanh hơn batch1 khoảng9% trên workload rất nhỏ này. Chưa chứng
 minh end-to-end6giờ. Không coi24 JSON hợp lệ là24 ý định đúng.
- Cùng batch,2lượt raw output trùng. Đổi batch làm khác trường `reason`;
 các field còn lại trùng trên4prompt đã đo. Không claim batch invariance chung.

## Dữ liệu, cấu hình và provenance

[Thiết kế](../docs/research/p2_intent_prompt_cache.md),
[plan](../docs/research/p2b_context_probe_plan.md),
[phạm vi P2c/ba khảo sát CPU](../docs/research/p2c_domain_scope.md).
16câu dev chọn bằng hash, tối đa2business/cụm và2câu/business; không chọn bằng
gold. Câu hỏi + descriptor A-T2 thực qua projection metadata có omission flag;
không sample values/row preview/absolute cache path/business ID trong prompt.
Không upload gold/type gold/alias/calibration/holdout. Payload/provenance chỉ local
`runs/p2b-dev-payload-20261107/`; CLI rebuild từ scoped dev và schema/hash nguồn
trước upload. Mẫu40gold ở khảo sát CPU riêng không vào inference.

Qwen3-14B revision `40c069824f4251a91eefaf281ebe4c544efd3e18`, weights P1
được hash lại, mount read-only, inference network blocked. RTX-PRO-6000 sm_120;
vLLM0.11.1,torch2.9.0/CUDA12.8,Python3.11.18 đúng pins. Cùng CUDA image digest
P1. BF16,TP1,seed0,temperature0,max_output256,eager,prefix/result cache tắt,
max_num_seqs4. `max_num_batched_tokens=max_model_len`; engine allocation target
29GiB dành1GiB margin, acceptance sampled total-device peak<=30GiB. Đây không
phải physical GPU partition hoặc hard memory limiter.

App [ap-gnP5ylDtx8Kx1K3w8UYSW8](https://modal.com/apps/vuonghungnguyen07/main/ap-gnP5ylDtx8Kx1K3w8UYSW8),
evidence key `d805a56c19964be89680d9cf2eee7dbe` trong Volume dev riêng.
Local `runs/p2b-context-20261107/`: preflight/events/result/summary,
config outputs/logs trên Volume. Một job, không retry; app đã kết thúc.
Account vuonghungnguyen07 và app inventory kiểm trước job; người dùng xác nhận
credit>=30USD trong phiên. Estimate bảo thủ20USD, ceiling30USD, không hard cap.
[Giá chính thức](https://modal.com/pricing) kiểm07/11: RTX0,000842USD/s;
CPU0,0000131/core/s, RAM0,00000222/GiB/s. Billing thực chưa có; không ghi0USD.
Build/startup/usage/storage có thể phát sinh riêng, không coi phép tính tài
nguyên yêu cầu là bill hoặc cận trên cứng.

## Context4096

16prompt thực dài739–7013token;8prompt vừa budget4096 gồm output reserve256.
Chọn4 quantile độ dài trong tập vừa, nguyên prompt, không cắt JSON/câu hỏi.
Workload chung mỗi lượt7318prompt token. Startup engine34,759s; warmup84,455s
tách khỏi đo. KV0,84GiB =5504token, log maximum concurrency cho4096token là1,34x:
batch4 là4request gửi cùng lúc, không chứng minh4sequence đầy4096 cùng resident.

| Batch request | Trung bình wall s/4request | Request/s (gộp2lượt) | Output token/s |
|---|---:|---:|---:|
| 1 | 38.506 | 0.1039 | 6.804 |
| 2 | 39.198 | 0.1020 | 6.863 |
| 4 | 35.345 | 0.1132 | 7.384 |

Không có latency từng request; walltime cả batch không được đổi tên thành
p95 latency. Mẫu4prompt lặp không đại diện phân bố dev/private; số token/độ dài
và initialization phải tính riêng khi dự toán P3. Chỉ có JSON validity và
reproducibility syntactic, không có gold evaluation hoặc semantic accuracy.

## Context8192 và quyết định tiếp theo

16prompt vừa token budget lý thuyết nhưng engine từ chối trước generation.
Weights27,5185GiB, KV khả dụng0,29GiB; cận KV một chuỗi8192 cần1,25GiB.
Sampled peak 29.739GiB trước init thất bại không là peak
của inference8k. Không dùng phép tính KV từ P1 để bỏ qua activation/workspace
khác khi thay prefill budget/max_num_seqs.

P2c có thể dùng4096 làm cấu hình đầu bảo thủ, giữ abstain cho prompt không
vừa hoặc không đủ evidence. Cần rút projection theo metadata/dev nếu muốn
mở rộng; không tune bằng public/calibration. Chưa có lý do bắt buộc TP2/FP8
chỉ xét evidence memory; chưa kết luận tầng LLM đáp ứng ngân sách thời gian.
Nếu8k trở thành yêu cầu, thí nghiệm mới nên tách prefill-token-budget khỏi
context với chunked prefill, đo lại cùng memory/throughput; chưa chạy hoặc
chứng minh phương án đó. Không tự retry cấu hình khác trong job này.

## CPU và review

Gate trước cloud:417passed/2skipped75,79s, Ruff/format pass, source unchanged;
`runs/cpu-check-20261106T172637094966Z-yu3jw975/gate.json`, đã đọc JSON/ba log,
harness passed/current, không warnings/errors.12test mới synthetic gồm guard,
projection, duplicate/extra keys, schedule, nguồn stale và no-gold prepare.
Source-prefix lỗi thiếu `data/` đã có regression RED→GREEN trước job.
Review độc lập chỉ source/spec/synthetic: không Critical/Important. Reviewer
không đọc dữ liệu BTC; parent kiểm scope/hash/audit/account/CPU và job thực.

Ba minor hoãn: checkpoint ngay sau init/warmup; lưu sanitized stderr khi
snapshot verification lỗi; giới hạn từng filter string trong schema. Hiện
output token/byte cap vẫn chặn output không giới hạn. Sửa trước dùng adapter
production; không suy probe này đã là inference integration/domain acceptance.

Gate cuối sau cập nhật tracker: **417passed/2skipped77,22s**, Ruff/format pass,
source không đổi, JSON/ba log đã đọc:
`runs/cpu-check-20261106T174519857830Z-x32dseth/gate.json`.
Fingerprint `720a9e1aa5dc23721245cde5f4c1d031fbd53336da94b8ab1650af7e4ae72fde`.
UTF-8/NFC QA8tệp pass; chỉ P2 active. CI GitHub kiểm riêng sau push.

## Bổ sung sau review07/11

38,506s/4request tương đương9,6265s/request ở batch1. Ngoại suy tuyến tính
đúng workload này:1000câu khoảng2,67giờ và3000câu khoảng8,02giờ/GPU, chưa gồm
load/business analysis/data. Đây là cảnh báo phải xử lý trước full dev/model,
không là benchmark toàn dev/private. KV5504token hạn chế concurrency nhưng
probe chưa cô lập nguyên nhân eager/prefix-cache/output-length. Khoảng7output
token/s gồm prefill/scheduler, không phải pure decode speed.

8/16prompt quá budget4096 chỉ mô tả mẫu đã chọn, không chứng minh một nửa
1895câu sẽ abstain. Tương tự154câu không thấy lọc không chứng minh coverage150.
[Thiết kế P2c CPU và performance gate](../docs/research/p2c_cpu_design.md)
chọn prompt business riêng và intent ngắn, output enum/index<=64token;
chưa chạy probe cấu hình mới hay đạt mốc0,28request/s/GPU.
