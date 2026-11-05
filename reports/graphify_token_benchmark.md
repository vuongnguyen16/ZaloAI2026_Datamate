# Token benchmark Graphify: một audit luồng run-eval

Ngày 05/11/2026, giờ Việt Nam. Kết quả của một replay truy xuất có kiểm soát,
không phải hai phiên Codex/LLM độc lập hoặc số billing của phiên chat này.
Protocol chốt trước tính token: [research note](../docs/research/graphify_token_benchmark.md).

## Kết quả

Graph dùng **26,716 token** cho navigation + source + skill.
So với đọc toàn codebase: **giảm 77.80%**.
So với rg rồi đọc nguyên file liên quan: **giảm 27.21%**.
So với rg chỉ đọc đúng đoạn: **tăng 12.22%**.

| Cách truy xuất | Navigation | Source | Skill riêng | Tổng task | Cộng context chung |
|---|---:|---:|---:|---:|---:|
| Đọc toàn bộ 49 file Python | 443 | 119,921 | 0 | **120,364** | 150,889 |
| rg + nguyên 11 file liên quan | 1,593 | 35,110 | 0 | **36,703** | 67,228 |
| rg + đúng các đoạn cần thiết | 1,593 | 22,214 | 0 | **23,807** | 54,332 |
| Graph + cùng các đoạn source | 4,095 | 22,214 | 407 | **26,716** | 57,241 |

Đơn vị token, tokenizer `tiktoken==0.12.0`, encoding tham chiếu `o200k_base`.
Đếm text thực bằng [tiktoken chính thức](https://github.com/openai/tiktoken),
không ước lượng chars/4; không khẳng định đây là tokenizer billing của model
Codex đang dùng. Dấu phẩy trong bảng phân cách hàng nghìn.

Context khởi động chung cố định **30,525 token**, gồm question,
read_first, skill DataMate và timeline DOCX đã trích text; không chứa data/gold.
Khi tính cả context chung, graph là **57,241** so với
**150,889** khi đọc toàn corpus: giảm
**62.06%**;
so rg-scoped thì tăng **5.35%**.

## Câu hỏi được chọn

> Audit toàn bộ luồng datamate run-eval: CLI truyền tham số thế nào; manifest, source và ledger được kiểm tra ra sao; ai được đọc gold dev/calibration, vì sao holdout và inference bị từ chối trước mở gold; reader xử lý file gold chung và ID nằm cuối record thế nào; missing/invalid prediction và 9 type được chấm ra sao; metadata có thể bypass policy không; paired bootstrap ghép cặp, lấy mẫu và hạn chế significance thế nào; output dev/calibration khác nhau gì; phát hiện input thay đổi trước ghi kết quả thế nào, có thật sự atomic không; những test synthetic nào chứng minh?

Chọn vì đi qua 7 file implementation + 4 file test, với 12 nhóm bằng chứng;
không tuyên bố đã chứng minh đây là câu hỏi khó nhất tuyệt đối của codebase.
Corpus nền là đúng **49 file Python** của graph hiện hành, không gồm docs,
fixtures JSON hay dữ liệu BTC. Hai nhánh scoped đọc chính xác cùng payload
source **22,214 token**, cùng số dòng và hash.

## Vì sao có kết quả âm với đối chứng mạnh?

Graph navigation tốn 4,095 so với rg 1,593 token,
và tải skill thêm 407. Tổng overhead chênh
**2,909 token**; source cần xác minh không giảm thêm.
Đã tính cả status, broad query depth2/budget2400 bị truncation, 4 explain
(run_eval/read_scoped/authorize_access/score), và 1 path. Không bỏ lượt query
chưa tốt. Không cần fallback rg trong nhánh graph của lần đo này.

Phần lớn lợi ích so với đọc toàn repo đến từ giới hạn source theo câu hỏi;
rg-scoped cũng làm được việc đó. Kết quả này chưa chứng minh graph tiết kiệm
token hơn một agent đã biết symbol và tìm kiếm tốt. Graph vẫn cung cấp cạnh
gọi/import để định hướng, nhưng không thay source ở audit có yêu cầu chính xác.
Không tự đổi cấu hình/skill chỉ từ một truy vấn.

## Kiểm tra chất lượng thông tin

12/12 nhóm dưới đây có source trong payload scoped và được tác giả review.
Đây là coverage bằng chứng, không phải điểm accuracy chấm mù của hai agent.
Các nhánh full-file/full-corpus chứa mọi đoạn tương ứng nên không thiếu facts.

| Nhóm | Source (đường dẫn tương đối trong repo) | Kết luận audit từ source |
|---|---|---|
| CLI | `cli.py:101–115,125–140` | CLI chỉ nhận dev/calibration; truyền split/hash/submission/output/policy và control/taxonomy/execution/replicates vào run_eval. |
| Frozen integrity | `splits.py:355–407,87–201` | open_split kiểm hash lock/manifest/policy, membership/leakage và ledger; verify_sources re-catalog source/labels/policy. Catalog này không đọc answers.jsonl. |
| Quyền đọc gold | `splits.py:468–518; scoped_data.py:177–250` | Purpose phải thuộc frozen policy; inference không được gold, calibration gold đòi evaluator, holdout gold luôn denied ở P0. authorize_access chạy trước routed_records mở gold. |
| Routing file chung | `scoped_data.py:16–174` | Quét bytes/envelope/ID toàn file, không JSON-decode answer/type/alias ngoài selected IDs; project_id xử lý ID cuối record. Có bound chiều dài/depth/số record, ID coverage và stat trước/sau. |
| Prediction/PA | `evaluation.py:19–50; scoring.py:242–282` | Unknown/duplicate/out-of-scope ID hoặc JSON invalid làm run invalid; missing/abstain =0, known-ID answer sai shape/type/value =−1, matched=+1. PA chia cho toàn bộ expected ID. |
| Matching 9 type | `scoring.py:10–307` | Decimal exact; percent HALF_UP 2 chữ số; string NFC/lower/giữ dấu và alias; date/boolean exact; list ordered; table align unique normalized names rồi row-set/bijective alias; unanswerable chỉ đúng cùng type. Corners vẫn provisional. |
| Metadata bypass | `evaluation.py:120–155,174–231; ingest/loader.py:39–47` | Submission/control/policy/taxonomy/execution phải regular/external, disjoint raw/frozen và không alias/hardlink. Bound size, kiểm provenance/coverage và execution record. Calibration không nhận detailed taxonomy. |
| Bootstrap | `evaluation.py:60–117` | Cùng unique ID/metadata; ghép candidate/control theo ID; sample business và leakage group, weighted bởi số câu, seed offset, percentile95. Dưới10 leakage clusters thì significance_claim_allowed=false. |
| Dev/calibration output | `evaluation.py:258–329` | Dev có per_question và new_error_ids; calibration chỉ aggregate. Report không xuất gold answer/alias; không gán evaluator time thành inference time. |
| Freeze/output integrity | `evaluation.py:304–329; artifacts.py:16–20` | Re-hash submission/policy/control/metadata và re-open split trước mkdir/write. Directory phải mới và disjoint. write_json dùng write_text, rồi mới per_question: output không phải transaction atomic cho toàn bộ bộ file; lỗi ghi có thể để lại output một phần. |
| Access audit | `splits.py:410–465; scoped_data.py:199–249` | Authorization-only ghi allowed và gold_content_read=false; reader ghi completed/failed với progress. Ledger có sequence/hash chain; writer có exclusive lock, flush/fsync. Đây là app guard, không phải OS ACL. |
| Regression synthetic | `tests/integration/test_evaluation.py; test_splits.py; tests/unit/test_evaluation_stats.py; test_scoring.py` | Có canary ngoài authorized ID, denied-before-open, invalid eval/bootstrap trước gold, metadata smuggling, stale/tampered sources/ledger, calibration aggregate, paired bootstrap deterministic và matching corners. CPU gate kiểm các test; không chạy gold BTC. |

## Kiểm chứng và tái lập

Payload text đầy đủ, command stdout/stderr, source ranges/hash, coverage JSON,
counts, script và dependency lock giữ local tại
`runs/graphify-token-benchmark-20261105/`. Không truyền code tới tokenizer
service; tokenizer chạy CPU local, chỉ tải bảng BPE công khai có hash.
Graph dùng backend none và analysis ghi input/output LLM tokens0.
Code corpus và graph SHA giữ nguyên trước/sau đo.

Recount từ payload đã chụp (không chạy truy vấn mới hoặc phụ thuộc state mới):

```powershell
.tools/uv/uv.exe run --project runs/graphify-token-benchmark-20261105 --locked python runs/graphify-token-benchmark-20261105/report.py
```

Chạy `benchmark.py` cùng môi trường để replay navigation/source trên working
tree mới; corpus phải vẫn49 file và graph current. Context startup mới có thể
khác vì tracker/state đã được cập nhật sau khi lấy snapshot. `report.py` chỉ
recount snapshot đã lưu. Cả hai script nằm trong run ignored, không thêm
dependency vào runtime DataMate hoặc tool Graphify chính.

Kiểm nhạy `cl100k_base`: graph giảm
77.99% so toàn corpus,
giảm 27.40% so rg-whole-file,
và tăng 12.19% so rg-scoped.
Kết luận về dấu của chênh lệch không đổi.

Giới hạn: một câu hỏi, một repo, graph có sẵn. Tác giả chọn/review kế hoạch
truy xuất cả hai phía, có kiến thức trước từ phiên setup và khảo sát; chưa phải
A/B độc lập. Common context được tính một lần/nhánh; không có system/tool
schema ẩn, envelope chính xác của host, reasoning, output answer generation,
cache billing, chi phí xây graph ban đầu hoặc toàn bộ lịch sử chat này.
Không suy ra mức tiết kiệm trung bình, PA/B0/model quality hoặc thời gian LLM.

## Cổng kiểm chứng DataMate

`uv run --locked python scripts/timeline.py check`: current, DOCX hash không đổi.
`uv run --locked python scripts/check.py`: **238 passed in 59.25s**, Ruff/format pass;
source không đổi trong gate. Evidence `runs/cpu-check-20261105T131103849645Z-am9z_ztn/gate.json`. Đã đọc JSON và ba stage
log; context P1 passed/current, ready, không warnings. P1 vẫn todo; không mở
model/Modal/gold/B0/PA. Đây là kiểm CPU và test synthetic, không kiểm chứng
accuracy của hai câu trả lời LLM độc lập.
