# Trạng thái dự án

Cập nhật 01/11/2026, giờ Việt Nam.

**Phase hiện tại:** S00 đã có CPU harness local và smoke CPU trên Modal chặn egress. P00 đã đối chiếu contract ban đầu, còn thiếu artifact chính thức để nghiệm thu. Chưa B0.

**Phiên bản chạy ổn định:** package `datamate` 0.1.0, CPython 3.11.18, uv 0.13.6, dependencies trong `uv.lock`. Không chọn model thật.

**Bằng chứng gần nhất:** 20 tests pass + lint/format; cổng cố ý sai trả exit 1; smoke local đúng 12.35/0012; stub train 3.000 output đúng ID và 3.000 log; cloud CPU smoke đúng 2 câu, egress probe thất bại và app completed. Chi tiết trong `reports/s00_setup.md`.

**Config:** `configs/smoke.yaml` cho fixture nhỏ; `configs/modal_dev.yaml` profile/workspace `vuonghungnguyen07`, ngân sách 30 USD/thí nghiệm. Token đã xác thực; không đổi active profile của máy. Source core không phụ thuộc Modal SDK.

**Quyết định còn hiệu lực:** local chỉ CPU nhẹ/fake; model thật trên Modal; không đọc gold vào inference; chưa upload dữ liệu BTC; không dùng public/private test để training/tuning. Raw giữ nguyên, hash trong `manifests/kit_files.json`.

**Chưa kiểm chứng:** GPU/model/offline model; Docker candidate trên cloud host tương đương BTC; full runtime/budget; evaluator semantics/PA; revision/deadline chính thức; quyền upload kit; backup kit ngoài ổ D.

**Việc tiếp theo có phạm vi rõ:** hoàn thành P00 bằng evaluator/runner/Docker guide và thông báo hiện hành từ BTC. Đối chiếu input mount/entrypoint/output với các artifact đó, chạy format stub qua runner/scorer và cập nhật requirements/open_questions. Song song có thể chuẩn bị script inventory P01, nhưng khóa split theo business trước nghiên cứu sâu câu/nhãn. Chưa chọn model hoặc mở rộng framework.

**Cách tiếp tục ở phiên mới:** đọc README → file này → tasks/backlog.json → docs/requirements.md, kiểm tra diff rồi chạy `uv run --locked python scripts/check.py`. Không coi trạng thái kế hoạch ban đầu là bằng chứng công việc đã hoàn thành.
