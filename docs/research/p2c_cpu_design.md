# P2c CPU và điều kiện trước full dev

Ngày07/11/2026, trên main6ac467e. Thuộc P2 đang active, không thay G2 hoặc
timeline. Nguồn: scope P2c đã chốt, rulebook SHA740267bc…23d113, báo cáo P2b,
review người dùng07/11 và contract runtime21600s/15B/2GPU.

## Nhận định và quyết định

9,63s/request ở batch1 là walltime trung bình của workload, không phải p95
hay pure decode latency. Khoảng7output token/s gồm cả prefill/scheduler.
KV5504token hạn chế concurrency, nhưng chưa tách tác động eager/cache/độ dài
output để kết luận một nguyên nhân duy nhất.154 câu không thấy dấu hiệu lọc
không là coverage;8/16 prompt quá dài không là tỷ lệ trên toàn dev.

CPU làm trước: mọi phép tính dùng Decimal và ngày bằng code; mapping rõ,
không đoán schema/trạng thái/đơn vị từ gold hoặc ID. Chỉ hỗ trợ net line
amount có nghĩa sau giảm giá dòng, không dùng tổng đơn gồm VAT/ship/voucher.
Mapping/nguồn phải có hash; chưa có mapping thật được kiểm thì chưa claim
business đó đã hỗ trợ. Không chỉnh raw hoặc join receipts để tính chỉ số.

## Data adapter

`BoundSource` gồm role `lines`/`headers`/`events`, column binding và iterator
`RawRow` có tọa độ/cells gốc. Có thể nhận từ raw DuckDB/CSV adapter sau này;
increment CPU này kiểm bằng synthetic, chưa tự suy binding cho18business.
Không thêm nhánh business ID. Mọi alias trạng thái/format ngày/số là explicit.

Gom theo mã đơn; header một-một hoặc dòng đơn có ngày/trạng thái nhất quán.
Blank carry chỉ khi binding cho phép, trong cùng source và cùng nhóm đơn;
không carry tiền/sản phẩm. Dedupe chỉ dòng cùng đơn có toàn bộ cells gốc giống
nhau, giữ mọi source coordinate; hai mã đơn khác nhau vẫn tính riêng.
Event trả/huỷ loại đơn trước lọc kỳ, kể cả ngày event sau as_of_date. Ngày event
không trở thành ngày đặt. Status/ID/date mơ hồ => abstain, không default completed.

Tiền thiếu/sai chỉ làm revenue của tập đơn liên quan abstain; order_count
không cần đọc tiền. Header lặp không nhân dòng. Header có đơn nhưng thiếu
detail không tự suy doanh thu0. Hạn số dòng/bytes, vượt thì abstain thay vì cắt.
Extent dữ liệu lấy từ các ngày đặt được chứng minh; ngoài extent abstain,
giao một phần tính phần giao; gap trong extent có thể0. Đây là extent bảo thủ,
không tự mở rộng từ bảng kho/thu tiền.

Entity filter phân biệt scope order/line; resolve code hoặc exact normalized
alias duy nhất, không fuzzy. Không hiểu dimension/mention, alias trùng hoặc
thiếu entity value có thể ảnh hưởng kết quả => abstain. Không lọc bỏ im lặng.
Revenue lọc line rồi cộng; order_count đếm mỗi đơn có line phù hợp một lần.

## Resolver và hai hàm

Resolver nhận cụm kỳ riêng, full-match: ISO/ngày D/M/Y, khoảng bao gồm hai đầu,
tháng/quý/năm tuyệt đối; hôm nay/hôm qua, tuần này/trước (Mon), tháng này/trước,
năm nay/YTD, N ngày gần đây. Kỳ thiếu năm theo rulebookL34. So sánh tháng này
tháng trước cùng số ngày, clamp cuối tháng; không áp luật đó cho mọi loại kỳ.
Lunar/Tết cần calendar source đã chuẩn hóa: chưa hỗ trợ thì explicit abstain,
không hard-code lịch. Không gọi resolver là hoàn tất toàn bộ B1/C1.

`revenue_total(ledger, period, filters)` cộng net dòng bằng Decimal, làm tròn
VND ở cuối theo policy hiện hành. `order_count` đếm mã đơn unique hợp lệ.
Ngoài scope ném `DomainAbstain(code)`, để entrypoint formatter chuyển abstain.
Chưa nối predict/model trong increment này, không fake thành B0/G2.

## Prompt/throughput trước full dev

Chọn tách hai tầng. Business analysis nhận descriptor theo chunk vừa context,
cache theo content+code+model+rulebook hash; output chỉ đề xuất binding có
evidence, CPU verifier mới công bố capabilities. Một business có thể cần hơn
một chunk; không giả định descriptor dài tự nhiên vừa4096.
Question prompt chỉ question/as_of/capabilities/candidates, mục tiêu<=1024
token theo tokenizer thật. Output không reason tự do, enum/index tới các kỳ
và bộ lọc CPU đã tạo, mục tiêu<=64token; truncated/unknown filter => abstain.

Mốc trước đo:3000question trên2replica độc lập trong<=5400s cho toàn tầng LLM,
gồm business analysis/load/warmup; floor0,28request/s/GPU chỉ là steady-state
floor cần thiết, chưa đủ. Nếu TP2, đo aggregate>=0,556request/s, không nhân đôi
throughput của một engine. Điều kiện tổng15B và cách tính replica phải được
đối chiếu contract trước triển khai2replica; không suy model nhỏ hơn tự hợp lệ.

Probe mới giữ BF16, thử prompt ngắn trước rồi CUDA graphs/prefix cache, seq8/16
nếu vừa30GiB; tách prefill token budget khỏi context. CUDA graph cũng tốn VRAM,
không bật mù. Đo cold/warm/cache hit-rate, từng request latency p50/p95, throughput
và peak với cùng workload; kiểm short-intent validity/loss of filters. Chỉ chạy
full1895dev qua model sau khi có evidence budget; CPU core không bị chặn.
Batch sort ổn định theo business/ID, lưu assignment/schedule/config và kiểm
output lặp; sort không tự bảo đảm deterministic CUDA scheduling.

P5 mới bake-off FP8/model8B khi có lý do thời gian/chất lượng; câu P2b “chưa
bắt buộc TP2/FP8” chỉ nói evidence memory, chưa kết luận ngân sách thời gian.
Credit/billing trước GPU kiểm lại; báo actual dashboard nếu đọc được, không
đổi giá GPU10phút thành bill gồm CPU/RAM/build/storage hoặc ghi0USD.
