# Nghiệm thu P0 đo lường

Ngày 05/11/2026. Scope hoàn tất P0-SPLIT, P0-SCORER, P0-TAXONOMY và cổng G0.
Không chạy model/Modal/Docker, không public submission, không commit/push.
Review self-review; không có reviewer độc lập. Cổng CPU cuối ghi ở phần dưới.

## Thành phần đã triển khai

- Split business/template/file đã khóa 18/6/6 business, 1895/397/708 câu.
  Hash manifest `b28dd4fa7fb34b7a0ed356c7ec11f32f84911bcdf71fcd128c2c5082b208fa18`
  giữ nguyên; [P0-SPLIT](p0_split_results.md).
- Scorer 9 type từ DOCX có nguồn/hash, strict schema, Decimal exact, alias,
  list/table matching và policy provisional; [hướng dẫn](../docs/evaluation.md).
- `run-eval`, report/per-question log dev, metadata route/runtime, control và
  paired bootstrap 1000 lượt theo business + leakage component, CI95.
- Reader gold/questions theo ID được authorize; scanner không giải mã value
  ngoài scope. Raw shared gold file vẫn được đọc byte/ID, không gọi đó là chưa
  mở file gold. Không decode type/answer/alias calibration/holdout trong acceptance.
- Taxonomy dev, aggregate coverage phần sealed và source/rule hashes; ledger
  access và public giữ đúng split policy, không có release holdout.

## Kết quả kiểm trên train

| Type gold dev | Số câu |
|---|---:|
| number | 1195 |
| percent | 373 |
| list | 130 |
| date | 83 |
| string | 52 |
| unanswerable | 34 |
| table | 16 |
| boolean | 12 |

Tổng 1895 dev; metadata 3000 câu train được đối chiếu, 397 calibration và 708
holdout không mở semantic gold. Dev có 519 câu ASCII-only, 34 unanswerable
(1,794%). Họ heuristic: revenue 1037, order_count 203, quantity 166, pricing77,
returns_cancellations52, inventory51, cùng các họ khác; 157 `other` và 456
multi-candidate được giữ rõ. Không có human-reviewed family accuracy claim.
Top họ cho P2 là gợi ý theo dev, cần rà `other`/ambiguity khi mở domain_lib.

Taxonomy v1 thiếu 816 `other`; đã rà 35 câu dev theo question-hash để bổ sung
dthu/bnhiu/hnay/hqua, telex và cách hỏi đơn vị/tiền. Chỉ dùng câu hỏi/type,
không chọn bằng gold answer hoặc PA; v1/v2 và bản G0 giữ riêng trong runs.

Lượt all-abstain contract probe: 0 correct/0 wrong/1895 abstain, PA=0.
Control giống candidate, ΔPA=0, cả CI bằng0; dev có18 business/4 leakage groups,
claim significance bị tắt vì quá ít cụm. Đây không phải model hoặc B0.
Runtime inference unavailable, không dùng runtime evaluator làm throughput.

## Nguồn và lỗi đã giải quyết

DOCX hash `9d28162bbe2ddcc6373279bc29935c7899f05bb5e736f631de06a4beb19b782e`,
body table2/table3 và paragraph24. Percent halfway/signed zero, partial/duplicate
column names, nested alias interpretation, null và malformed known-ID còn
provisional trong [policy](../configs/scoring_policy.json), không chờ BTC runner.

Probe đầu dừng vì scalar-only alias validator gặp alias lồng ở dev line19,
chưa ra PA. Schema-only inspection dev ghi nhận65 list alias arrays và16
table row arrays; bổ sung bounded positional/bijective matching có regression.
Giữ freeze ban đầu/v2; không xóa lỗi hoặc đổi expected để pass. Progress audit
đã thêm cho lỗi đọc; lần prototype đầu có note phục hồi, số partial decoded
record không xác định, guard dev-only khi đó vẫn hoạt động.

Contract registry chỉ đổi3 trường trạng thái project scorer/matching/Docker
P3; mọi luật/giới hạn BTC giữ nguyên. Data/kit manifest/lock/config môi trường/
Docker giữ nguyên; split không chia lại. Gold reader xuất hash/envelope counts,
không xuất answer/alias. Artifact thật chỉ ở runs ignored.

## Bằng chứng và cổng cuối

64 tests mới về matching/precision/nested aliases, routing sentinel ngoài dev,
deny trước file-open, metadata/raw-gold bypass, bootstrap, taxonomy và audit.
CPU scorer trước hardening: 224 tests pass trong48.78s, Ruff/format pass tại
`runs/cpu-check-20261105T111324672996Z-okkznoge/`; đây là bằng chứng trung gian.

Acceptance hiện hành: `runs/p0-complete-20261105/g0_acceptance-current.json`
valid=true, source161 file không đổi; 5685 authorized record decodes trong
lượt cuối (question dev + gold dev taxonomy + gold dev evaluation), ngoài dev=0.
Manifest/policy/rules và code hashes current. Live deny holdout/evaluator và
calibration/developer pass; public/release ledger rỗng. Chi tiết trong
`taxonomy-g0/`, `evaluation-g0/`, `implementation_freeze_g0.json`.

Cổng CPU/handoff cuối: `.tools/uv/uv.exe run --locked python scripts/check.py`,
exit0, **232 passed in36.59s**, Ruff/format pass; JSON/ba log đã đọc tại
`runs/cpu-check-20261105T113049158829Z-92zldnf2/`. Source không đổi trong gate.
`final_acceptance.json` valid=true, fingerprint khớp source/gate hiện hành;
92 tệp UTF-8/NFC/JSON, 83 local links, diff check pass. Artifact hashes current,
161 source file và gold bytes khớp kit gốc; contract chỉ đổi3 trường project,
payload luật BTC giữ nguyên. Tất cả4 task P0 done; context P1 ready, P2 blocked,
không warning. CLI run-eval thật exit0 với taxonomy/control; help taxonomy pass.
Không stage/commit/push dữ liệu hoặc source trong increment; chưa CI mới.
