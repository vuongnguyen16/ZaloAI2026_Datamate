# Phép đo token Graphify: một truy vấn audit nhiều module

Ngày 05/11/2026. Người dùng yêu cầu tự chọn truy vấn phức tạp và đo phần trăm
token tiết kiệm. Chọn luồng đánh giá P0 vì có CLI, manifest/source integrity,
policy/access ledger, JSON byte routing, scorer, thống kê và output guard.
Không khẳng định đã chứng minh đây là câu hỏi khó nhất trong mọi câu hỏi có thể.
Không chạy evaluator trên dữ liệu BTC hoặc mở gold.

## Câu hỏi khóa trước khi tính số token

“Audit toàn bộ luồng `datamate run-eval`: CLI truyền tham số thế nào; manifest,
source và ledger được kiểm tra ra sao; ai được đọc gold dev/calibration, vì sao
holdout và inference bị từ chối trước mở gold; reader xử lý file gold chung và
ID nằm cuối record thế nào; missing/invalid prediction và 9 type được chấm ra sao;
metadata có thể bypass policy không; paired bootstrap ghép cặp, lấy mẫu và hạn chế
significance thế nào; output dev/calibration khác nhau gì; phát hiện input thay
đổi trước ghi kết quả thế nào, có thật sự atomic không; những test synthetic nào
chứng minh các guard đó?”

## Thiết kế

Đây là replay truy xuất có kiểm soát, không phải hai phiên LLM mù/độc lập.
Tác giả đã biết một phần code từ phiên setup và khảo sát graph ban đầu. Chốt
protocol trước khi tính token; không thử nhiều câu hỏi rồi chỉ chọn kết quả tốt.

So sánh cùng corpus Python đang được graph lập chỉ mục:

1. Đọc toàn corpus một lần: mốc tham chiếu cho “đọc codebase”.
2. `rg` rồi đọc nguyên các file liên quan: mốc đọc theo file.
3. `rg` rồi đọc đúng các đoạn cần dùng: mốc đối chứng mạnh.
4. Graph rồi đọc chính các đoạn source đó: tính cả navigation, status và skill.

Giữ nguyên bộ bằng chứng source giữa (3)/(4), có số dòng và hash. (1)/(2)
phải chứa đầy đủ bằng chứng đó. Không tính output graph ngắn là đã trả lời đủ.
Bao gồm broad graph query depth2/budget2400 đã bị truncation trong chi phí
navigation, rồi explain các symbol để thu hẹp. Không xóa lượt query chưa tốt.
Đối chứng rg gồm file inventory và tìm declaration/CLI/test liên quan; không
đọc vùng data/runs. Không dùng knowledge graph JSON nguyên khối làm context.

Đếm bằng `tiktoken==0.12.0`, encoding tham chiếu `o200k_base`, kiểm nhạy bằng
`cl100k_base`; không đoán tokenizer billing của model Codex hiện tại. Dependency
và lock riêng trong thư mục run, không đổi môi trường DataMate/Graphify.
Tokenizer BPE là công cụ CPU, không phải model weights/embedding.
Nguồn API: [tiktoken chính thức](https://github.com/openai/tiktoken).

Đếm text nguyên vẹn của từng payload bằng cùng encoding, cộng payload; gồm
command hiển thị và source có số dòng. Báo task-specific và tổng cộng context
khởi động chung theo read_first/timeline/skill DataMate. Không cộng hai lần
context chung. Không tính system/tool schema ẩn, tool envelopes, reasoning,
answer generation, cache billing hoặc toàn bộ lịch sử chat này. Những chi phí
đó không có telemetry riêng từng nhánh ở môi trường hiện tại.

## Coverage và acceptance

12 tiêu chí phải có source: CLI; freeze integrity; role/purpose/partition;
JSON routing; prediction/score; type matching helpers; metadata guard;
bootstrap; dev/calibration outputs; hash lại input/output non-transactional;
ledger audit; tests canary/denied/invalid/metadata/bootstrap.
Kiểm completeness bằng các range source đóng băng và review tác giả, không gọi
đó là điểm accuracy độc lập của hai agent.

Công thức `100 * (baseline_tokens - graph_tokens) / baseline_tokens` cho từng
mốc; số âm nghĩa là graph dùng nhiều token hơn. Giữ và báo cả kết quả âm.
Một query/một repo chỉ là case study; không suy ra mức tiết kiệm trung bình.

Lưu script, pyproject/lock, payload đầy đủ, source hashes, counts và review trong
`runs/graphify-token-benchmark-20261105/` (ignored). Báo cáo công khai chỉ chứa
thống kê, phương pháp và vị trí source code, không dữ liệu/gold BTC.
