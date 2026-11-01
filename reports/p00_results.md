# P00 — Kết quả triển khai và nghiệm thu contract

Ngày 01/11/2026, giờ Việt Nam. **P00 hoàn thành theo đặc tả trong thể lệ và công cụ project.** BTC không cung cấp runner/evaluator riêng theo xác nhận của người dùng; không đặt việc tìm executable BTC làm điều kiện chuyển bước. Scorer matching/PA thuộc P02; đây chưa phải B0.

## Kết quả

| Hạng mục | Train | Public test |
|---|---:|---:|
| Câu hỏi kiểm tra schema/ID | 3.000 | 1.000 |
| Business được tham chiếu | 30 | 14 |
| Output unique IDs, khớp input | 3.000 | 1.000 |
| Missing / duplicate / unknown IDs | 0 | 0 |
| Log hợp lệ, answer khớp submission | 3.000 | 1.000 |
| Nội dung gold được mở | Không | Không |

Output là `abstain` cho mọi câu: chỉ chứng minh contract/đường chạy. Không báo PA, coverage chất lượng model hoặc khả năng giải nghiệp vụ từ kết quả này. Public test chỉ dùng kiểm tra cơ học, không đọc đáp án hoặc tuning prompt.

Rulebook hai split có hash khác nhau, calendar có cùng hash. Runner manifest giờ lưu hash questions/rulebook/calendar. Kit raw và thể lệ được rehash, không đổi so với `manifests/kit_files.json`.

## Thay đổi đã giữ

- Plan v1.3 và các state/backlog/runbook thống nhất: Docker hoãn toàn bộ tới P13 khi pipeline/cấu hình hoàn chỉnh; không thay đổi Dockerfile/.dockerignore nháp trong increment này. Modal Image vẫn dùng khi cần chạy cloud.
- `docs/requirements.md` có requirement ID, nguồn/section/paragraph và cách kiểm tra; `manifests/competition_contract.json` lưu schema/paths/model limits/deadlines và policy project; model inventory ghi đủ field cần thu thập ở P04.
- `validate-input` kiểm tra thành phần split, business references và cấu trúc calendar; không phân tích nội dung bảng/README hoặc gold.
- `validate-submission` kiểm tra type/value, JSON strict và ID; phát hiện duplicate keys/NaN, duplicate/unknown IDs. Missing output được báo abstain theo thể lệ; `--require-complete` là policy riêng để phát hiện runner bỏ sót.
- `validate-logs` kiểm tra coverage, thời gian, evidence và final answer khớp submission.
- `predict.sh` giữ default `/data` và `/result`, cho override input/output bằng env để test shell ngoài Docker; không triển khai inference thật.

## Kiểm chứng đã chạy

`uv` là bản workspace `.tools/uv/uv.exe` nếu chưa có PATH; dùng env cache/Python theo README.

```powershell
uv run --locked python scripts/check.py
uv run --locked python scripts/verify_p00.py
uv run --locked python scripts/audit_kit.py
```

Cổng CPU: **34 tests passed**, Ruff lint/format pass. 14 ca P00 bổ sung có negative cases về input thiếu thành phần, business reference sai, missing predictions, JSON duplicate keys, type mismatch, unknown/duplicate IDs, log lệch submission hoặc thiếu log và exit code CLI. Không đổi expected output chỉ để pass.

`scripts/verify_p00.py` tạo run mới chứa stub và artifact/log cho cả hai split, ghi aggregate metadata vào `reports/p00_contract_checks.json`; file này chứa run path và hash registry dùng khi nghiệm thu. Lệnh exit 0 khi cả input/submission/logs đều hợp lệ. Không dùng network/GPU/model.

Shell thực được kiểm tra bằng Git Bash: chạy `predict.sh` trên fixture synthetic với `DATAMATE_INPUT_DIR`/`DATAMATE_OUTPUT_DIR`, sau đó `validate-submission --require-complete` và `validate-logs`; cả ba exit 0. Artifact ví dụ: `runs/p00-shell-f03b7e4ee1e148ecbb6d303a5ecc8bcc/`. Không suy ra container mount/permission từ shell test này.

## Nguồn và phạm vi

Đã đọc DOCX trong `Thể lệ cuộc thi/` và xác nhận không có embedded executable/hyperlink. Website [DataMate](https://challenge.zalo.ai/portal/datamate) được kiểm tra Overview và các tab Evaluation/Rule/Submission Guidance; [Timeline](https://challenge.zalo.ai/#timeline) xác nhận deadline. Source evidence trong `manifests/p00_sources.json`.

Một lượt browser trước dừng ở tab Data cần đăng nhập, không thu được nội dung các tab khác; không dùng lượt đó làm bằng chứng đã đọc Rules. Lượt riêng sau đã đọc ba tab công khai. Không đăng nhập, thay đổi tài khoản, gửi dữ liệu hoặc nộp bài. Xác nhận người dùng rằng không có runner/evaluator riêng đã được ghi thành nguồn workflow; không yêu cầu người dùng tìm công cụ không tồn tại.

## Giới hạn và bước tiếp theo

P00 chưa tính matching/PA và chưa đọc sâu nhãn. Những corner case như rounding tie, alias, table matching/null/extra fields sẽ có research note và policy minh bạch ở P02, khi đã khóa split. Không gọi validator/scorer project là công cụ BTC.

GPU/model/eligibility checkpoint ở P04; Docker/OCI digest/mount read-only và full offline runtime ở P13. P00 không phát sinh job Modal mới, không tải model hoặc publish raw.

**Bước tiếp theo: P01** — inventory metadata/cấu trúc, nhóm business có nguy cơ trùng và khóa split development/calibration/holdout trước nghiên cứu sâu câu/nhãn. Giữ implementation P00.
