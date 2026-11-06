# Quyết định phạm vi P2 và cổng G2 G5

Ngày 06/11/2026. Nguồn: timeline DOCX hiện hành, backlog, split lock/scoped
evaluation P0, bằng chứng P1 và phản biện người dùng chuyển lại trong phiên.
Các đề xuất trong bản phản biện không được tự gán cho người chuyển tiếp.
Người dùng đã chốt bộ ngưỡng G5 và hai điều chỉnh bằng điểm ròng sau lựa chọn
giữ dự thảo trước đó; xác nhận mới thay thế trạng thái dự thảo.

Đây là quyết định cho increment P2 và cổng P5, không là tracker/roadmap mới.
State/backlog vẫn là tracker duy nhất. Chưa có code P2, probe mới hoặc PA mới.

## Quyền dữ liệu đã ghi nhận

Chủ project xác nhận được dùng dữ liệu BTC trên Modal; phạm vi làm việc P2
được cụ thể hóa trong phiên này: chỉ input/câu hỏi dev và artifact tối thiểu
của dev trên Modal, gồm descriptor/prompt cần cho probe. Không đưa gold
calibration/holdout lên cloud; các partition này tiếp tục theo access policy
đã khóa. Gold không đi vào inference. Gold dev chỉ dùng qua scoped evaluator
để chấm local trong phạm vi hiện tại, không cần upload cho probe context.
Không chuyển quyền Modal sang API khác hoặc quyền publish dữ liệu lên GitHub.
Mỗi job vẫn kiểm đúng account/workspace và budget tối đa30USD/thí nghiệm;
không hỏi lại quyền Modal đã có khi công việc nằm trong phạm vi này.

## P2 và G2 thu gọn

Thứ tự: ghi quyết định/đồng bộ nguồn → lưới an toàn → probe BF16 context và
throughput với prompt dev thật → vài họ nghiệp vụ ưu tiên → đánh giá dev →
G2 mới → đóng gói P3. Chỉ một task active; không mở P5 cùng lúc.

Lưới an toàn đi trước nghiệp vụ: formatter9type, abstain mặc định, hạn từng
câu/toàn lượt, cô lập dòng/câu lỗi và giữ các dòng hợp lệ tiếp tục chạy.
Không tự tạo ID cho dòng không route được; lỗi input được báo riêng, không
claim toàn input hợp lệ. Với tập ID hợp lệ đã xác định, luôn hoàn tất output
đủ ID bằng abstain cho câu lỗi/chưa xử lý. Checkpoint nối tiếp từng câu gắn
hash input/config; resume chỉ khi hash khớp. Không phá tính chất bảo vệ file
cũ: không ghi đè artifact đã có, finalize qua file tạm và đổi tên an toàn.
Log tối thiểu gồm ID, route/status, reason/error, duration và provenance.

P1 chỉ thử max_model_len2048, không đo trần context. Probe P2 phải đếm token
prompt thực (có dự phòng output), đo KV capacity, peak memory và throughput
1/2/4 chuỗi với độ dài đại diện trong trần30GiB/GPU. KV dùng chung cho các
chuỗi: ước tính160KiB/token và2.12GiB tương đương khoảng13.9k token tổng,
không chứng minh2–4 chuỗi8k cùng lúc. BF16 trước; TP2/FP8 chỉ xét khi có
nhu cầu và bằng chứng riêng, không bật đồng thời nhiều biến để che nguyên nhân.
Đây là giả thuyết cần đo, không phải throughput/khả năng RTX5090 đã được xác nhận.

G2 mới: mọi ID hợp lệ có output đúng shape; PA trên toàn dev>0; tỷ lệ sai
wrong/(correct+wrong)<=10% trên phần trả lời (mục tiêu nội bộ), báo coverage
và số abstain theo type/business/route/family. Không đặt cổng độ phủ tối thiểu
hoặc bắt buộc đủ5họ. Vài họ chọn theo tần suất/lỗi dev, mỗi hàm có test và
chạy đúng trên>=2nhóm; phần chưa phủ abstain. Rulebook/calendar có nguồn,
giữ raw/lineage khi cleaning tối thiểu; descriptor rút gọn dùng trong prompt
chọn hàm/ý định phải có bằng chứng thực, không thay bằng synthetic consumer.

SQL fallback chuyển sang P4 tối thiểu và P5 tối ưu; single_sql đối chứng
chuyển P5. Tracing mở rộng chuyển P4–P5, log tối thiểu giữ ở P2. Năm họ là
mục tiêu mở rộng theo lỗi tại P4, không còn điều kiện G2. Public#1 chỉ chuẩn
bị và gửi theo scope/quota được xác minh; không dùng lượt public chọn cấu hình.
P3 vẫn ngay sau G2; không chờ SQL hoặc các tối ưu P4–P5.

Hiệu chỉnh ngưỡng liên kết thực thể: P4 chỉ dùng ngưỡng tạm trên dev;
chọn/khóa ngưỡng bằng calibration ở P6. Đã sửa cả B4 trong DOCX và acceptance
P4 để không yêu cầu mở calibration trước pha được phép.

## G5 đã chốt trước thí nghiệm

Nhãn: **quy tắc quyết định kỹ thuật, không phải ý nghĩa thống kê**.
Contract máy đọc: `configs/g5_decision_policy.json`. P5 cần tích hợp/check
contract này; hiện bootstrap chỉ cung cấp báo cáo, chưa là implementation G5.

Với mỗi câu, score thuộc{-1,0,+1}. Điểm ròng là tổng(score_candidate-score_control),
không phải số câu thay đáp án: sai→đúng đóng góp+2. Dùng cùng ID dev cố định,
cùng model/revision/tokenizer, seed và scorer; đối chứng là cấu hình đang
được chấp nhận, đóng băng trước mỗi thí nghiệm. Thay model là bake-off riêng,
cần protocol khai báo trước, không được gọi là so sánh kỹ thuật cùng model.

- Kỹ thuật mới: deltaPA>=+0.01; vớiN=1895 cần>=19điểm ròng.
- Đơn giản hóa/bỏ kỹ thuật: deltaPA>=-0.005, có bằng chứng giảm độ phức tạp;
  vớiN=1895 được giảm tối đa9điểm ròng. Không gán nhãn đơn giản hóa để né cổng.
- Cả hai nhánh: ít nhất3/4cụm có điểm ròng>=-1 (định nghĩa dung sai của
  "không giảm"); mọi cụm có điểm ròng>=-max(N_c/100,2), tương đương
  deltaPA_c>=-max(0.01,2/N_c). Dùng số hữu tỉ/Decimal, không làm tròn float.
  Ngưỡng mất điểm nguyên là floor(max(N_c/100,2)).
- Kỹ thuật phải nằm trong ngân sách runtime được đo tại P3, kể cả load/IO
  và workload đã khai báo. Vượt ngân sách thì loại dù PA tăng.
- Báo CI95% bootstrap theo business và cụm rò rỉ,>=1000lượt, nhãn **mô tả,
  không phải cổng**. Business trong cùng cụm có tương quan; khoảng theo
  business không chứng minh ý nghĩa thống kê. Không dùng `internal_decision`
  cũ của paired_bootstrap làm cổng G5 mới; split/access/thuật toán P0 giữ nguyên.

Dev có thể overfit qua nhiều vòng chọn. P5 không chấm từng kỹ thuật trên
calibration. P6 chỉ chọn ngưỡng và kiểm cấu hình cuối theo policy; không dùng
lỗi từng câu calibration để viết hàm/prompt. Holdout mở một lần tại P7.

## Lựa chọn và phép kiểm

Giữ G2 cũ đủ5họ+SQL trước đóng gói bị loại vì kéo dài lát cắt đầu. Chọn G2
ít họ, ưu tiên độ đúng, có log/abstain; đánh đổi là PA dương có thể thấp do
coverage thấp. G5 giữ cổng CI dương bị thay bằng tiêu chí kỹ thuật đã chốt;
đánh đổi là không được claim significance từ4cụm hoặc bỏ kiểm tổng quát hóa.

Kiểm giấy tờ: DOCX/web/asset/backlog cùng hash; quyền/state không mâu thuẫn;
công thức biên điểm ròng đúng, không sửa split/access/scorer để tăng điểm.
Kiểm triển khai tiếp theo: failure/kill-resume/finalize tests synthetic, CPU
gate, probe model thật có account/budget/data manifest, PA dev scoped; báo riêng.
