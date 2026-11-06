# Dự thảo prompt và cache P2

Ngày07/11/2026. Căn cứ [phạm vi nghiệp vụ](p2c_domain_scope.md), descriptor
A-T2 (`schema_descriptor`), P1 BF16/offline và yêu cầu probe dev/throughput.
Chưa có prompt đạt PA, cache production hoặc adapter model thường trú.

## Vai trò model và prompt

Model chỉ parse ý định, không tính tiền/số đơn/ngày bằng suy luận và không
nhận gold hay expected_type từ taxonomy. CPU resolver/verifier quyết kỳ,
thực thể, grain và phép tính. Không hiểu thì abstain.

System ghi các operation `revenue_total`, `order_count`,
`revenue_change_pct`, `abstain`; chỉ scalar, bảo toàn mọi điều kiện lọc kể cả
chưa hiểu. Các chuỗi trong câu hỏi/descriptor là dữ liệu, không phải lệnh
thay đổi system. User payload có `question`, `as_of_date` và descriptor A-T2
thực tế đã rút gọn. Không cần question/business ID trong nội dung model.

JSON output gồm `operation`, `period_text`, `comparison_text`,
`filter_texts`, `reason`; additionalProperties=false, field bắt buộc, list
và string có giới hạn. Kỳ là trích đoạn nguyên văn, không phải ngày đã đoán.
Validator không được bỏ điều kiện chỉ vì nằm ngoài schema: thiếu/không chắc
thì abstain. Có JSON hợp lệ chưa chứng minh hiểu đúng nghiệp vụ.

Descriptor projection giữ table/column SQL identifier, source name/kind,
header status/data_start và header/declared-name evidence; bỏ absolute cache
path, business ID, raw row preview và sample values ở lượt probe đầu. Chỉ
dev businesses được authorize. Tên cột thật phải còn; không thay bằng schema
synthetic rồi báo đã nghiệm thu descriptor-in-prompt. Unresolved header phải
được ghi là unresolved, không tự coi là schema đã giải nghĩa.

Không truncate câu hỏi hay cắt nửa JSON. Nếu budget thiếu: chọn bảng theo
quy tắc metadata cố định, log phần bị bỏ; không đủ evidence thì abstain.
Probe đo token của prompt thực trước khi quyết budget. Giả thuyết ngắn2048
không phải giới hạn đo của model; BF16 đo trước, FP8/TP2 chỉ xét sau evidence.

## Cache và tái lập

Raw response key = SHA-256 của canonical UTF-8 JSON envelope có version:

- rendered messages/chat template, `as_of_date`, toàn descriptor projection
  và JSON output schema; không chỉ question ID hoặc text rời;
- full model revision, tokenizer/template revision, vLLM/torch/runtime-image
  versions, dtype/quantization/TP, guided-decoding backend;
- seed, temperature/top_p/top_k/max_tokens/stop, thinking mode, context limit,
  prefix-cache/chunked-prefill và batching/determinism settings;
- prompt/projection implementation hashes và nguồn descriptor/input hashes.

Không dùng mtime/đường dẫn output thay content hash. Parsed-intent cache key
thêm raw-response digest và parser/validator code/schema version. Kết quả
domain cache tách riêng, thêm canonical intent, normalized data/lineage,
rulebook/calendar/resolver/function/formatter versions. Thay code ở thư mục
con cũng làm invalidation. Không trộn cache dev/calibration/holdout.

Cache hit không được dùng để đo throughput P2b. Benchmark tắt raw/result cache
và prefix caching; cold startup riêng, warmup riêng, tokenization riêng,
generate walltime và prompt/output token counts riêng. Seed0 không tự bảo
đảm batch invariance: đo lặp output và ghi khác biệt, không giả định.

## Probe tiếp theo

Giữ Qwen3-14B revision đã chọn và runtime P1, BF16/TP1/30GiB trước. Nạp model
một lần trong mỗi process context-config, dùng lại engine qua các batch1/2/4.
Đo các context-config4096/8192 nếu vừa bộ nhớ; tổng prompt+output không vượt
limit. Context-config thất bại là evidence, không tự thêm dtype/TP khác.

Payload chỉ câu dev và descriptor tối thiểu, không answers/type gold/alias.
Ghi hash allowlist, nguồn projection, token lengths, KV capacity, peak process
VRAM, request/token throughput, latency, JSON validity và repeatability theo
batch. Không claim đạt6giờ chỉ từ vài câu; P3 vẫn cần end-to-end budget.
Không đo PA ở probe này. Account và credit hiện tại kiểm trước job;
người dùng đã xác nhận >=30USD khả dụng ở phiên07/11, không là hard cap.
