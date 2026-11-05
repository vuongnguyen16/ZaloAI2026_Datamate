# P0-SPLIT khóa split và access policy

> Bằng chứng tại thời điểm freeze split, trước P0-SCORER. Scoped reader và
> dev-gold access hiện đã có ở [P0 đầy đủ](p0_results.md); các câu "gold chưa
> mở/ledger rỗng" bên dưới mô tả thời điểm nghiệm thu split, không phải hiện tại.

Ngày 05/11/2026. Đã tạo split train thật, policy/hash/provenance, access audit
và public submission ledger. Scope không gồm scorer/taxonomy/model hoặc nộp bài.
Review do tác giả thực hiện; audit bằng thuật toán riêng không phải reviewer khác.

| Partition | Business | Câu hỏi | Cụm độc lập |
|---|---:|---:|---:|
| dev | 18 | 1.895 | 4 |
| calibration | 6 | 397 | 3 |
| holdout | 6 | 708 | 2 |

60/20/20 theo business; câu hỏi có số lượng khác nhau. Giữ nguyên 9 cụm nối
bắc cầu từ template/file A-T2 và preamble layout README; thêm 17 schema SQLite.
Holdout chỉ có 2 cụm, nên bootstrap business phải kèm sensitivity theo cụm và
giới hạn ý nghĩa thống kê. Không đổi split theo điểm; chưa có điểm nào được đo.
Mọi input train đã từng được khảo sát; holdout chỉ sạch về đáp án, không thể
gọi là hoàn toàn unseen input/domain. README layout chưa phải nhãn ngành xác nhận.

Manifest thật chỉ ở `runs/p0-split-20261105/frozen/manifest.json`, SHA-256
`b28dd4fa7fb34b7a0ed356c7ec11f32f84911bcdf71fcd128c2c5082b208fa18`.
Pointer không chứa membership: [split lock](../manifests/split_lock.json).
Spec trước code: [research](../docs/research/p0_split.md);
[hướng dẫn/policy](../docs/split_policy.md).

## Bằng chứng thực chạy

- `uv run --locked python .tmp/run_p0_acceptance.py`: exit 0, 2.93s.
  Hai lần tạo có cùng manifest hash; không thay raw, protected config/lock/kit
  manifest/Docker. 161 input file được đối chiếu hash (158 file business và
  questions/rulebook/calendar); gold chỉ kiểm stat, không mở để hash/parse.
- Guard `Path.open` trong acceptance từ chối mọi thao tác mở `answers.jsonl`;
  toàn freeze/repeat/verify/audit vẫn pass. Không đọc public/private content.
- Audit membership riêng đủ 3.000 ID không trùng/mất; 441 signature/edge từ
  evidence/raw/README không cắt qua partition. Liệt kê độc lập 3^9 phương án
  xác nhận độ lệch tỷ lệ business tối ưu bằng 0. Không tách cụm để ép tỷ lệ.
- Coverage 322 CSV/XLSX unit và 17 SQLite table. Labels A-T2 đúng hash freeze;
  không sử dụng partition dev/check cũ để gán QA membership.
- `uv run --locked datamate split-check --split runs/p0-split-20261105/frozen --manifest-sha256 b28dd4fa7fb34b7a0ed356c7ec11f32f84911bcdf71fcd128c2c5082b208fa18`:
  valid=true; không mở gold.
- Regression riêng: **18 tests pass trong 3.69s**, gồm bắc cầu/determinism,
  stale/missing labels, ID trùng, output overlap, public input bị từ chối,
  source/manifest/policy/ledger mutation, role/purpose, SQLite và workbook coverage.
  Lượt đầu pytest lỗi vì parent scratch chưa tồn tại; tạo directory rồi chạy lại,
  không bỏ test hoặc đổi expected để pass.

Access API chỉ cấp quyền/ID scope và ghi audit, chưa là gold reader. Holdout
gold luôn bị từ chối trong P0; không unlock bằng chuỗi `P7`. P0-SCORER phải nối
evaluator/gold reader vào policy; P7 mới triển khai release một lần với gate/
predictions/config hash. Ledger thật access/public/release hiện rỗng.
Hash chain/lock không thay ACL/mã hóa hoặc chống rollback cùng tài khoản.

Protocol khóa: paired bootstrap ≥1.000 lượt theo business, seed 20261105,
CI95% percentile; thêm cụm leakage sensitivity; public chỉ format/crash/gap,
tối đa một lượt/pha nội bộ, không chọn ngưỡng/prompt/model bằng public.
Bootstrap/scorer chưa triển khai; không dùng policy JSON để tuyên bố PA pass.

CPU gate cuối: `.tools/uv/uv.exe run --locked python scripts/check.py`, exit 0,
**168 passed in 34.70s**, Ruff/format pass; đã đọc JSON và ba stage log tại
`runs/cpu-check-20261105T105244828707Z-h1gedsfm/`. Source không đổi trong gate.
Final proof `runs/p0-split-20261105/final_acceptance.json` valid=true, builder và
manifest đúng hash, source fingerprint trùng CPU current; 161 source file và
protected config/lock/kit manifest/Docker không đổi, không mở gold. 79 tệp
UTF-8/NFC/JSON, 69 link local hợp lệ, diff check pass; không stage dữ liệu.
Context P0-SPLIT done/P0-SCORER ready; taxonomy/G0/P1 vẫn blocked; không warning.
Không commit/push hoặc chạy CI mới; GPU/model/PA chưa chạy. Lệnh acceptance
đã chạy như trên, driver lưu tại `runs/p0-split-20261105/acceptance_driver.py`;
reproduction cần output mới, không ghi đè frozen split.
Evidence local: `runs/p0-split-20261105/acceptance.json`, `input_hashes.json`,
`protected.json`, `frozen/`, `repeat/`; artifact BTC không stage/publish.
