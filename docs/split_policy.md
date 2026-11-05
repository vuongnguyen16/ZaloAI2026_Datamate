# Split train và quyền truy cập đã khóa

Nguồn thiết kế: [P0-SPLIT](research/p0_split.md), Timeline hiện hành §8.
Policy thực thi: [configs/split_policy.json](../configs/split_policy.json).
Pointer/hash split thật: [manifests/split_lock.json](../manifests/split_lock.json).
Manifest chứa membership/metadata BTC chỉ giữ local trong
`runs/p0-split-20261105/frozen/`; không copy hoặc sửa `data/`.

| Partition | Business | Câu hỏi | Cụm leakage độc lập |
|---|---:|---:|---:|
| dev | 18 | 1.895 | 4 |
| calibration | 6 | 397 | 3 |
| holdout | 6 | 708 | 2 |

Tỷ lệ 60/20/20 theo business; số câu không bằng nhau. Giữ cả cụm nối bắc cầu
theo full header A-T2, file trùng byte và preamble bố cục README. SQLite bổ sung
schema catalog. Seed/thuật toán khóa trước chạy; không chọn lại bằng PA.
Holdout chưa xem đáp án, nhưng input/structure toàn train đã được khảo sát và
dùng nghiên cứu header. Bố cục không phải taxonomy ngành đã xác nhận.

## Kiểm tra và dùng

```powershell
$split = Get-Content -Raw -Encoding UTF8 manifests/split_lock.json | ConvertFrom-Json
uv run --locked datamate split-check --split $split.artifact_directory --manifest-sha256 $split.manifest_sha256
```

Lệnh kiểm hash manifest/policy/source/A-T2 evidence và ledger, không mở gold.
Mất artifact local thì khôi phục đúng bản đã khóa hoặc tái tạo rồi đối chiếu
hash; không chia lại sau khi xem gold/chọn cấu hình. Pointer repo không chứa
answers, question text hoặc danh sách business/câu hỏi.

Lệnh tái tạo kiểm determinism, chỉ trước truy cập gold và dùng output mới:

```powershell
uv run --locked datamate split-freeze --input data/train --structure-labels runs/a-t2-completion-20261105/labels_frozen.json --labels-sha256 3eb90b23bf13b185559a4d1a87f7c6a932044d0e654b2410c3e66d24d8815ef6 --policy configs/split_policy.json --output runs/p0-split-reproduction-new
```

## Ranh giới truy cập

| Phần | Được dùng | Không được dùng |
|---|---|---|
| dev | Viết hàm/prompt, taxonomy, training, đánh giá | Hardcode theo business/question ID |
| calibration | Evaluator đo/chọn ngưỡng và kiểm tối ưu | Developer đọc gold viết hàm hoặc huấn luyện |
| holdout | Input cho inference với cấu hình đóng băng | Gold trước P7, chọn cấu hình, viết hàm/prompt |
| public/private | Nộp/kiểm format/runtime/gap theo scope | Training, tuning hoặc chọn biến thể |

`split-access` là **authorization và audit**, trả ID được phép; không nạp
gold/câu hỏi/context. Caller phải dùng scope này trong pipeline. Gold reader
của [P0-SCORER đã nối vào policy](evaluation.md); không đưa nhãn holdout cho
người chọn cấu hình. API không thay ACL/mã hóa: người có cùng quyền hệ điều
hành vẫn có thể đọc trực tiếp file.

P0 không có lệnh unlock holdout, kể cả purpose `P7`. P7 phải có evaluator riêng,
gate P6 được chấp nhận, predictions/config/commit hash khóa và consume ledger
release một lần **trước** mở gold. Chuỗi tên pha không mở khóa. Tối ưu P8 sau
P7 cần đánh giá độc lập mới hoặc công bố giới hạn.

Access/public/release ledger khởi tạo rỗng lúc freeze. P0 hiện đã có dev access
audit; public/release vẫn rỗng. Access request ghi cả cho phép/từ
chối, candidate hash và mục đích; không ghi answer. Hash-chain phát hiện sửa
event, khóa exclusive tránh hai writer; không chống rollback/truncation bởi
người cùng tài khoản. Interrupted writer để lại khóa phải rà trước retry.

## Thống kê và leaderboard

PA theo câu; candidate/control cùng ID, resample ghép cặp theo business với
hoàn lại ≥1.000 lượt, seed 20261105, CI percentile 95%. Báo thêm sensitivity
resampling theo **cụm leakage** vì business cùng template có phụ thuộc.
Với chỉ 4/3/2 cụm, không dùng CI làm bằng chứng mạnh về unseen-domain
generalization. Báo số cụm/giới hạn; không đổi split theo điểm.
Scorer/bootstrap đã triển khai ở P0-SCORER theo protocol được khóa tại đây.

Public chỉ format/crash/generalization; tối đa một lượt/pha theo policy nội bộ,
không dò ngưỡng/prompt/model/biến thể nhỏ. `split-log-public` ghi receipt, phase,
purpose, candidate/submission hashes; không gửi submission. Quota BTC hiện hành
phải xác minh lúc nộp. Nhật ký hiện rỗng, chưa có lượt public trong increment.
