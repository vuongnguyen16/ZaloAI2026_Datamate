# Contract DataMate cho các nhóm A–G

Giữ các yêu cầu từ thể lệ, tách khỏi roadmap. Nguồn đã đối chiếu ngày
01/11/2026: `Thể lệ cuộc thi/The_Le_Zalo_AI_Challenge_2026_DataMate.docx`,
kit local và website BTC; provenance ở `manifests/contract_sources.json`,
registry ở `manifests/competition_contract.json`, hash ở `manifests/kit_files.json`.
Đây là quan sát lịch sử; kiểm tra lại quy định/lịch khi cần nộp hoặc chọn model.

**BTC không có runner/evaluator executable theo xác nhận của người dùng.**
Validator/runner là code project; scorer P0 đã xây từ quy tắc thành văn,
có [policy provisional và scoped evaluator](evaluation.md).
Không gọi validator hoặc fake smoke là kết quả chấm điểm hoặc baseline chất lượng chính thức.

| ID | Yêu cầu được giữ | Nguồn | Bằng chứng/giới hạn |
|---|---|---|---|
| I01 | Question: id, business_id, question, as_of_date ISO; không dùng ngày máy | DOCX §1 ¶8–17, Overview | Schema/validator hiện có |
| I02 | Split có questions/rulebook/calendar và data/business_id với README, CSV/XLSX/SQLite | DOCX §3.2 ¶77–89, kit | Loader A-T1, runtime format/header/profile A-T2 đã nghiệm thu; actual prompt integration ở P2 |
| I03 | Rulebook/calendar đúng split, giữ provenance/hash | DOCX §3.4 ¶109, kit | Hai rulebook khác hash; calendar cùng hash |
| O01 | JSONL id/type/answer; reason tùy chọn; 9 type | DOCX §2.1, §3.5 ¶117–127 | Strict shape/type + project matching P0; corners provisional |
| O02 | Missing answer tính abstain; PA=(correct−wrong)/N | DOCX §2.1–2.3 ¶21,67–70,127 | Project scoped scorer; require-complete là policy runner, chưa model baseline |
| O03 | predict.sh đọc /data, ghi /result/submission.jsonl và /result/logs | DOCX §3.5 ¶128 | Stub/shape có sẵn; chưa inference thật/container |
| R01 | Inference offline, input read-only, temp ngoài input | DOCX §4 ¶137,141 | Modal synthetic chặn egress lịch sử; chưa Docker/full run |
| R02 | Tổng inference ≤15B gồm auxiliary/all MoE params; weights trước 01/10/2026, license hợp lệ | DOCX §4 ¶134–135, public Rule | Chưa chọn model, kiểm tra D/G trước job |
| R03 | Không hard-code ID/đáp án, không training/tuning public/private test | DOCX §4 ¶139,143; policy project | Fake chỉ synthetic; inference không đọc gold |
| R04 | Máy mô tả 2×RTX5090 32GB, RAM512GB, ≤6h gồm load; rerun lệch PA≤0.03 | DOCX §4 ¶145,147, public Rule | Chưa đo GPU/full runtime/PA |

Output types: number, percent, string, date, boolean, list, table, unanswerable,
abstain. Type/value phải cùng đúng. Serializer/scorer corner cases như rounding
tie, alias lồng và table/null corners được ghi provisional; list order và
table row-set từ DOCX đã kiểm thử. Không coi project policy là executable BTC
hoặc bằng chứng model/B0.

Quan sát lịch sử: train 30 business/3.000 câu/162 file; public 14 business/
1.000 câu/97 file. Validator chỉ kiểm tra cấu trúc/reference/hash, không đọc
gold hoặc chấm câu hỏi public. Report giữ ở `reports/contract_checks.json`.

Thông tin lịch/quotas đã đọc ngày 01/11 nằm trong contract/provenance. Timeline
mới là tài liệu chia việc, không tự thay đổi các thông tin được ghi trong những
nguồn đó. Trước khi lập lịch hoặc nộp bài, cần xác minh thông tin hiện hành từ BTC.
Docker nháp chờ P3 thuộc G sau lát cắt P2/G2;
Modal Image không thuộc phần Docker bị hoãn.
