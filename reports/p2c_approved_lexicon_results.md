# P2c: áp lexicon người dùng đã duyệt — 08/11/2026

Tiếp nối `db32bc5`; người dùng duyệt đúng cột Proposed group của packet
`runs/p2c-semantic-review-20261108-v3/review-packet-local.md`, với chỉ dẫn
“Duyệt các nhóm đề xuất, giữ unknown”. Phạm vi chỉ lexicon, chưa duyệt nguồn.

## Receipt và ranh giới

- Bản nháp đã duyệt có SHA
  `2a52ddb7de1617801079a10942b4a1a4276a7863d567d53e1d55f6c78b3ac2a7`;
  xác minh byte nguyên vẹn trước chuyển trạng thái.
- Bản mới chỉ local `runs/p2c-status-approved-20261108/lexicon-approved.json`,
  SHA `85875bce7d95909cc52e27a5f148393ea04a5c78b6a7b893ab4687b869cd8a30`.
  23entry approved,6entry unknown;25khóa sau normalization hiện hành.
  Không thêm nghĩa mới ngoài Proposed group đã được duyệt.
- Receipt lưu thời điểm UTC, lời duyệt và draft/rulebook hash. Loader đã kiểm
  SHA, rulebook, scope, xung đột; bản nháp gốc và source-review vẫn giữ nguyên.
- Packet vai trò nguồn có SHA
  `7a6f114f682d5e001f16b7550b84749a8112fde6a2844a8e658cab261e95fb90`,
  vẫn pending. Lexicon approval không cấp source binding hoặc oracle-control.
- Không sửa STATUS mặc định hoặc code runtime; audit opt-in explicit vào
  artifact SHA. Không đọc gold, calibration/holdout, gọi model hoặc tăng guard.

## Audit đã chọn trước

Chạy cùng18dev/profile/nguồn/guard của baseline, mỗi worker nhận cùng lexicon
SHA. So với `runs/p2c-semantic-default-audit-20261108/`, báo riêng hai metric,
số business/cụm pass, regression và blocker còn lại. Đây là machine checks
trên binding hiện hành, không phải PA hoặc G2, không là duyệt source độc lập.

Lệnh thực:

```text
python scripts/p2_binding_audit.py audit
  --profile-index runs/p2c-binding-inputs-20261107/profile/profile.json
  --output runs/p2c-approved-lexicon-audit-20261108
  --status-lexicon runs/p2c-status-approved-20261108/lexicon-approved.json
  --lexicon-sha256 85875bce7d95909cc52e27a5f148393ea04a5c78b6a7b893ab4687b869cd8a30
```

## Kết quả thực

| Metric | Trước: business / cụm qua kiểm | Sau: business / cụm qua kiểm | Business còn unknown_status |
|---|---:|---:|---:|
| order_count | 1 / 1 | 1 / 1 | 13 → 10 |
| revenue_total | 1 / 1 | 1 / 1 | 13 → 10 |

18/18worker nhận đúng SHA được duyệt. Không business mới pass, không
regression. Source-role blocker vẫn12business, row-resource guard2;
header6/date3 giữ nguyên. Doanh thu còn arithmetic4/format4/net-semantics2/
scale1. Blocker đếm chồng, không cộng thành tổng business.

Observed count source-only tăng1business/1cụm lên3business/2cụm;
status+source-only giảm3/2 xuống1/1. Status-only vẫn4/2 và còn nhóm khác9/3.
Đây là thay đổi chẩn đoán sau khi gỡ status, chưa chứng minh ledger ở cụm thứ
hai.17business vẫn chưa có đủ bằng chứng scan/ledger hoàn tất.

Artifact so sánh local: `comparison-summary.json`, `comparison-local.json`
trong thư mục audit mới. Đã tách packet ưu tiên23source chưa rõ của3business/
2cụm, kèm27source context và điều khoản rulebook, tại
`priority-source-review-local.md` và `.json`; mọi quyết định nguồn vẫn pending.
Không đề nghị tự đổi6nhãn unknown đã được người dùng chọn giữ nguyên.

## Verification

Literal labels/member/packet/ledger giữ local. Full locked CPU sau cập nhật
tracker: **574passed/2skipped,123,80s**, Ruff lint/format pass; source không
đổi trong gate. Đã đọc gate.json và cả ba stage log tại
`runs/cpu-check-20261108T050931075922Z-3mp7smxr/gate.json`.
Harness P2 passed/current, không warning/planning error/task active khác;
timeline current, UTF-8/NFC4file và git diff check pass. Fingerprint so với
gate trước chỉ đổi backlog; không có code runtime/dependency mới.

Profile-index SHA vẫn khớp inventory18dev. Business dựng được ledger có
provenance so được với baseline và khớp;17record chưa qua kiểm không có đủ
ledger provenance, không suy chất lượng hoặc completeness từ đó. Artifact
lexicon/SHA và packet nguồn pending đã được kiểm lại sau audit.
