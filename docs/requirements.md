# P00 — Requirements và contract triển khai

Kiểm tra ngày 01/11/2026, giờ Việt Nam. Nguồn chính cho chi tiết là `Thể lệ cuộc thi/The_Le_Zalo_AI_Challenge_2026_DataMate.docx` người dùng chỉ định và kit local; SHA-256 trong `manifests/kit_files.json`. Đã đối chiếu thêm [DataMate](https://challenge.zalo.ai/portal/datamate) gồm Overview, Evaluation, Rule, Submission Guidance và [Timeline BTC](https://challenge.zalo.ai/#timeline). Registry: `manifests/competition_contract.json`; evidence nguồn: `manifests/p00_sources.json`.

**Người dùng xác nhận BTC không có runner/evaluator riêng.** P00 tự xây runner/validator từ đặc tả; P02 tự xây scorer từ quy tắc chấm. Không chờ công cụ BTC hoặc coi sự vắng mặt đó là blocker.

Nhãn **BTC công khai** chỉ áp dụng phần đã đọc trực tiếp trên website; **Tài liệu cung cấp** dùng cho chi tiết trong DOCX chưa đối chiếu được trên website; **Quan sát kit/Đã kiểm chứng** có lệnh hoặc artifact tái hiện. Chưa có version/changelog upstream của kit.

| Yêu cầu theo tài liệu | Nguồn | Cách kiểm tra / trạng thái |
|---|---|---|
| P00-I01: Question có `id`, `business_id`, `question`, `as_of_date`; ngày ISO, không dùng ngày hệ thống | BTC công khai Overview; DOCX §1, ¶8–17; quan sát kit | `validate-input` pass 3.000 train + 1.000 public; unique IDs và business refs hợp lệ |
| P00-I02: Split có `data/<business_id>/`, rulebook, calendar, questions; training có answers | Tài liệu cung cấp §3.2, ¶77–89; kit | 30/14 business, README và table files tồn tại; kiểm tra không mở gold |
| P00-I03: Rulebook lấy đúng split | Tài liệu cung cấp §3.4, ¶109; quan sát hash | Hai rulebook khác hash, calendar giống; stub manifest lưu cả rule/calendar hash |
| P00-O01: 9 kiểu output và JSONL `id/type/answer`; reason tùy chọn | BTC công khai Overview xác nhận types/ví dụ; DOCX §2.1, §3.5, ¶117–127 | Validator cấu trúc; strict type tránh bool thành number, NaN, date sai; không làm answer matching |
| P00-O02: Missing answer là abstain; PA = (correct − wrong)/N | Tài liệu cung cấp §2.1–2.3, ¶21, 67–70, 127 | Missing IDs được báo abstain; `--require-complete` là policy runner riêng. PA chưa đánh giá |
| P00-O03: `predict.sh` đọc `/data`, ghi `/result/submission.jsonl` | Tài liệu cung cấp §3.5, ¶128 | Shell entrypoint pass synthetic bằng override env; default giữ đúng contract. Docker test hoãn P13 |
| P00-O04: Log dưới `/result/logs/` có ID, final answer, thời gian và evidence code/results | Tài liệu cung cấp §3.5, ¶128 | 4.000 log có coverage và answer khớp submission; stub ghi rõ không chạy model/tool |
| P00-R01: `/data` read-only, temp nơi khác, inference offline | Tài liệu cung cấp §4, ¶137, 141 | Không sửa input; S00 Modal synthetic chặn egress đã chạy. Nghiệm thu mount/container hoãn P13 |
| P00-R02: Tổng mọi model inference ≤15B, tính cả auxiliary/all MoE params | BTC công khai Rule; DOCX §4, ¶134–135 | Policy registry + model inventory; chưa chọn model, phải kiểm tra ở P04 |
| P00-R03: Weights công khai trước 01/10/2026, license hợp lệ | BTC công khai Rule; DOCX §4, ¶135 | Registry dùng cutoff exclusive; model provenance/revision/license chờ P04 |
| P00-R04: Không can thiệp thủ công/hard-code IDs, không training bằng public/private test | Tài liệu cung cấp §4, ¶139, 143 | Stub abstain mọi câu, fake chỉ synthetic; public chỉ kiểm tra cơ học format/reference |
| P00-R05: Máy chấm 2×RTX 5090 32 GB, RAM 512 GB, job ≤6 giờ gồm load | BTC công khai Rule; DOCX §4, ¶145 | Ghi nhận làm mục tiêu P04/P13; chưa đo model trên hardware tương đương |
| P00-R06: Re-run lệch PA ≤0.03 | BTC công khai Rule; DOCX §4, ¶147 | Theo dõi ở P13; chưa có PA để đánh giá |
| P00-S01: Hạn giải pháp 23:59 ngày 16/11/2026 GMT+7; private 20/11 09:00 → 23/11 23:59 | BTC công khai Timeline; DOCX §5, ¶157–161 | Đã đối chiếu trang chủ; registry dùng ISO offset +07:00 |
| P00-S02: Public tối đa 5 lần/ngày; Docker tối đa 2 lần, chấm bản cuối | BTC công khai Submission Guidance; DOCX §5, ¶155, 158 | Chưa tự động nộp bài; xác minh lại cổng trước khi nộp |

## Quan sát kit

Train: 30 business directories, 162 file, 194.290.513 bytes, 3.000 câu. Public test: 14 business directories, 97 file, 109.361.117 bytes, 1.000 câu. Cả hai pass input/submission/log checks; bảng dữ liệu không được mở để phân tích trong P00. Calendar mỗi split có 1.461 dòng và các cột `date,weekday,lunar_day,lunar_month,lunar_year,lunar_leap,holiday`; semantics thuộc P07.

Sau khi người dùng chỉ lại thư mục thể lệ, đã quét lại cả file ẩn và cấu trúc DOCX: chỉ một DOCX 47.267 bytes, không có embedded executable hoặc hyperlink evaluator. DOCX chứa đặc tả chấm và contract chạy/nộp, đã được dùng làm căn cứ triển khai. Sau đó người dùng xác nhận BTC không có runner/evaluator: xác nhận cụ thể này quyết định workflow, không diễn giải thông báo evaluation software chung trên trang chủ thành yêu cầu phải tìm thêm executable. Tab Data cần đăng nhập; không cần đăng nhập thêm để tiếp tục P00.

## Giới hạn triển khai

Kiểm tra hình dạng đáp án không xác nhận semantics matching, đặc biệt rounding tie/alias/table order/null/extra fields. Chưa viết scorer ở P00; P02 xây scorer project từ §2 thể lệ và kiểm thử từng quy tắc. Những corner case không được quy định rõ mang nhãn `provisional`, không gọi là semantics chính thức. Stub không phải B0. `predict.sh` sẽ được thay bằng pipeline thật ở P05.

Theo yêu cầu chủ dự án, toàn bộ Docker hoãn tới P13 sau khi pipeline hoàn chỉnh; giữ nguyên Dockerfile/.dockerignore nháp. Docker không chặn P00–P12. P00 nghiệm thu bằng công cụ project theo đặc tả và kết quả trên kit thật; bước tiếp theo là P01.
