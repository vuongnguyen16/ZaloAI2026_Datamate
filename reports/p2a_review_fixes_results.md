# Sửa phản hồi Linux PR1 — P2a

Nguồn yêu cầu: phản hồi người dùng trên head2ddb03c,06/11/2026.
Thiết kế [p2a_review_fixes](../docs/research/p2a_review_fixes.md),
[plan](../docs/research/p2a_review_fixes_plan.md). P2 vẫn in_progress, chưa G2.

## Các thay đổi

1. `/result/logs` rỗng sẵn được nhận. State nằm logs/.state; log từng câu nằm
   logs/submission-<sha>/*.json, validator chọn theo final hash để không lẫn log
   attempt cũ. Có answer/status/reason/timing/provenance; replay thiếu timing
   ghi rõ timing_available=false. Root chỉ có submission và logs khi chạy sạch.
2. Timeout/error câu riêng được cô lập, thành công reset consecutive count.
   Startup/dead worker hoặc3lỗi liên tiếp mới vô hiệu backend. Budget output
   vẫn giữ headroom cho abstain.
3. `predict` CLI có wrapper bao config/import/run. Khi primary lỗi và chưa có
   final, fallback route ID bằng parser cú pháp questions-only, dedup SQLite
   và stream all-abstain; không decode answers/business hay checkpoint cũ.
   Công cụ dev run_predict vẫn strict. Input hardlink/ancestor alias/ID quá
   giới hạn dev có đường giảm cấp. Existing final và output trong input bị từ chối.
4. Publication opt-in xb+copy/fsync khi errno capability cho biết no-hardlink,
   nhãn non_atomic_exclusive trong kết quả/diagnostics. Không dùng fallback
   cho permission/disk error và không truncate file cũ hay file thắng race.
5. Hash source dùng rglob Python và relative subpackage path; cùng basename
   ở ingest/profile không đè nhau trong fingerprint.
6. README sửa riêng trong f33bf08, mô tả no_model/predict/checkpoint/failsafe.

## Bằng chứng đang chốt

Hai lỗi Linux chính đều tái hiện RED trước sửa và GREEN sau: logs có sẵn;
q1 timeout thật trong process còn q2–q4 trả lời7 từ fixture synthetic.
Test query error xen kẽ thành công, recursive code hash, startup/config failure,
hardlink/identity/inventory fallback, >10000IDs/dedup, existing-final preservation,
no-link errno/race/permission và CLI thật đã có.

Targeted36passed/1skipped trong36.97s. Skip mới là directory symlink do quyền
Windows; Linux CI phải chạy ca này thật. Test giới hạn10001IDs ghi final và
SQLite thật, dùng sink synthetic cho file log lặp lại; physical per-ID logs
được kiểm ở fixture nhỏ và CLI kill/resume2000IDs. Không dùng sink cho dữ liệu BTC.
Targeted là bằng chứng bước đầu; gate cuối sau fix review ghi dưới đây.

Review source/synthetic độc lập phát hiện thêm3Important: fallback vượt live
writer lock, vượt foreign-dir admission, import CLI/dependency sớm chưa được
catch. Đã thêm shared publication lock/guard, minimal emergency imports và
regression subprocess cho cả3. Case limit từng bị xếp Minor được nâng Important
vì valid=true che coverage thiếu; nay counter/coverage_complete/valid phản ánh đúng.
Các regression mới có6fail trước fix, thêm import Pydantic cũng fail trước;
sau fix8case pass. Không re-review vòng2; tác giả kiểm regression và toàn suite.

CPU cuối `uv run --locked python scripts/check.py`:394passed/2skipped trong69.51s,
Ruff/format pass, exit0, source không đổi. Đã đọc gate và3log tại
`runs/cpu-check-20261106T150301669878Z-gu4dqicp/gate.json`, fingerprint
`52f8c5682b3025075784065e8434f55ff9dfd6d4f4207c259e10d387cd368d8b`.
Hai skip là symlink fixtures do quyền Windows; CI Linux phải chạy thật.
CI exact-head và trạng thái merge xem [PR1](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/pull/1);
chỉ merge khi run tương ứng success, giữ expected_head_sha để không merge nhầm head.

## Giới hạn giữ rõ

All-abstain fallback không thể cứu một file questions không đọc được, ID không
parse được, disk không ghi được, hoặc OS kill trước fallback. File final cũ
không bị ghi đè kể cả không hợp lệ. xb không atomic: chết trong copy có thể
để lại final dở; diagnostics không phải hard guarantee khi process mất trước flush.
Resident model/batching/process groups và clock từ predict.sh vẫn P2b/P2c.
Không job Modal, model thật, Gold mới, PA, Docker hoặc public submission.

PR tạm draft vì GitHub không cho author Request changes trên chính PR mình (API422).
Người dùng yêu cầu sửa/gate/CI rồi merge; thực hiện theo exact-head CI và expected SHA.
Taxonomy top20 chỉ xuất hội thoại theo yêu cầu, không commit/push cells hoặc records.
