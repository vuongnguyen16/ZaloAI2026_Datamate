# Đánh giá DataMate trong phạm vi split đã khóa

Scorer project triển khai từ thể lệ DOCX §2.1–2.3 và alias §3.2; không phải
executable BTC. [Policy matching](../configs/scoring_policy.json) ghi hash
nguồn và các điểm provisional. [Thiết kế](research/p0_evaluation.md),
[kết quả P0](../reports/p0_results.md), [split/access](split_policy.md).

## Luật matching

| Type | Matching |
|---|---|
| number | Decimal exact; không tự làm tròn prediction, không tolerance |
| percent | Làm tròn 2 số thập phân, giữ dấu; halfway HALF_UP là policy tạm |
| string | NFC → lowercase → non-alnum thành space → gộp whitespace; giữ dấu; dùng alias gold |
| date | ISO ngày hoặc tháng, exact; không đồng nhất tháng với ngày đầu tháng |
| boolean | true/false strict, không coi 0/1 là boolean |
| list | Đúng số phần tử và thứ tự; string/number theo luật tương ứng |
| table | Cột theo full unique normalized-name mapping, không đủ thì positional; rows set |
| unanswerable | Chỉ correct khi gold cũng unanswerable |
| abstain/missing | 0; mọi đáp án còn lại correct +1 hoặc wrong −1 |

Alias lồng được quan sát ở dev: list theo vị trí, table theo hàng với đúng một
text cell đứng đầu. Policy tạm dùng alias cho text đó và matching song ánh
giữa row set; không suy sang nhiều text column hoặc shape chưa biết. Table
null cells hiện không hỗ trợ; partial/duplicate column-name fallback và malformed
known-ID policy cũng provisional. Không gọi các điểm này là BTC đã xác nhận.

JSON hỏng, duplicate/unknown/out-of-scope ID làm run invalid; answer sai shape
với ID hợp lệ tính wrong. Type abstain luôn 0 theo nguồn, dù payload thừa;
structural validator riêng vẫn có thể báo payload đó sai format.

## Chạy evaluator

```powershell
$p = Get-Content -Raw -Encoding UTF8 manifests/split_lock.json | ConvertFrom-Json
uv run --locked datamate run-eval --split $p.artifact_directory --manifest-sha256 $p.manifest_sha256 --partition dev --submission runs/my-run/submission.jsonl --output runs/my-eval-new --control runs/control/submission.jsonl --taxonomy runs/p0-complete-20261105/taxonomy-g0/taxonomy.json
```

Output mới, ngoài raw/frozen split. Prediction phải thuộc partition đã chọn;
missing ID=abstain, không đổi N. Optional `--execution` nhận JSONL mỗi ID có
`route` và `duration_seconds`; thiếu thì runtime/route ghi unavailable. Không
gán thời gian fake hoặc coi thời gian evaluator là inference.

Hash predictions/control/policy/metadata gắn trong report, kiểm lại sau chạy.
`evaluation.json` có PA/correct/wrong/abstain theo type/business/family/route;
`per_question.jsonl` của dev ghi score/diagnostic, không xuất gold answer/alias.
Calibration chỉ aggregate, không xuất per-question score hoặc taxonomy để viết hàm.
Bootstrap control dùng cùng ID, ≥1000 lượt ghép cặp theo business và sensitivity
theo leakage component, seed 20261105, CI95 percentile. Dưới 10 cụm độc lập
thì project không cho claim significance; đây là quy tắc bảo thủ nội bộ.

Quyết định06/11 cho G5: **quy tắc quyết định kỹ thuật, không phải ý nghĩa
thống kê**, theo [contract](../configs/g5_decision_policy.json) và
[quyết định](research/p2_g2_g5_decisions.md). Dev có18business nhưng chỉ4cụm;
business trong cùng cụm có tương quan. Cả CI business và CI cụm được báo với
nhãn **mô tả, không phải cổng**. `internal_decision`/CI acceptance cũ của
bootstrap và policy P0 không quyết định G5 mới; không sửa split/access đã khóa.
P5 cần tích hợp gate toàn dev/cụm/runtime, hiện chưa có implementation đó.

Kỹ thuật mới cần deltaPA>=+0.01; đơn giản hóa có bằng chứng cần>=-0.005.
Cả hai nhánh: ít nhất3/4cụm có điểm ròng>=-1; mọi cụm có điểm ròng>=
-max(0.01*N_c,2). Điểm ròng là chênh tổng score, sai→đúng=+2; không là số
câu thay đáp án. Với1895câu: kỹ thuật cần>=19điểm, đơn giản hóa giảm tối đa9.
Runtime phải trong budget đo P3. P5 chỉ dùng dev cho từng kỹ thuật;
calibration chỉ chọn ngưỡng/kiểm cấu hình cuối tại P6, holdout một lần P7.

Gold chung nằm một file. Reader đọc byte/ID của toàn file để routing, nhưng
chỉ JSON-decode record được authorize. Type/answer/alias của calibration/holdout
không được giải mã trong P0 acceptance. Không đưa raw gold vào submission,
policy hay metadata để bypass; các file ngoài phải regular, không alias/hardlink,
nằm ngoài raw/frozen split. Đây là guard ứng dụng, không thay OS ACL.
Access audit ghi request, completion hoặc lỗi với progress; denied gold dừng
trước mở file. Không có đường release holdout ở P0. Inference không gọi reader gold.

## Taxonomy

```powershell
uv run --locked datamate taxonomy --split $p.artifact_directory --manifest-sha256 $p.manifest_sha256 --output runs/taxonomy-new
```

Chi tiết chỉ dev: gold type, họ câu hỏi, operation, thời gian, viết tắt,
ASCII-only, ambiguity; classifier nhận question text/type, không nhận answer/alias.
Những nhãn ngoài type là heuristic và có `other`; không dùng như truth đã
được reviewer độc lập xác nhận. Coverage toàn train 3000, dev 1895, calibration
397 và holdout 708 sealed được báo riêng. Không chia lại split theo kết quả.

Scorer và bootstrap đã có nhưng chưa có model/B0. Lượt all-abstain P0 có PA=0
chỉ kiểm contract/coverage; không phải kết quả chất lượng của hệ thống.
