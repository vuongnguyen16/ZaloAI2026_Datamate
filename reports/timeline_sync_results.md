# Đồng bộ Timeline mới ngày 05/11/2026

Phạm vi: workspace và GitHub theo DOCX một người/P0–P9. Giữ A-T1/A-T2 và
foundation đã có bằng chứng; không thực hiện scorer/model/PA hoặc Docker.
Review bởi tác giả, không có reviewer độc lập.

- Archive đã push và đối chiếu peeled SHA: tag
  [archive/timeline-20261103](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/tree/archive/timeline-20261103),
  commit `bd0061593698df76c05745c7ef1df3d31b1331f3`. Dùng tra lịch sử.
- Dọn 8 tệp cũ: research/reset và report/reset; spec/report engineering A-T2
  tạm; prompt phản biện Claude; note khảo sát sơ bộ A-T1; report publish cũ;
  sơ đồ `image1.png`. Nội dung cần giữ đã có trong spec/report hoàn thiện hoặc archive.
- Viết lại README/state/backlog/AGENTS/skill/harness theo pha. 18 task gồm 3
  foundation, 1 migration, các task P0 và P1–P9. Task tuần cũ có mapping trong
  `manifests/timeline_source.json`; không còn task tuần đang chờ thực hiện.
- P0 khóa split trước taxonomy gold; G0 chặn P1; hybrid P2 giữ acceptance
  descriptor-in-prompt/PA; P3 đóng gói sau G2; P8a/P8b cần quyết định chạy/bỏ.
- Bản web được xuất lại bằng `scripts/timeline.py`: 129 đoạn văn ngoài bảng,
  20 bảng/149 dòng, một sơ đồ và link nguồn. DOCX giữ nguyên byte người dùng.
- Harness kiểm hash nguồn/web/ảnh/task, dependency thiếu/vòng, trạng thái skip
  và giới hạn một việc dở dang. Nguồn lệch chặn readiness; CPU fingerprint gồm
  backlog/manifest/bản web/ảnh để thay đổi kế hoạch không dùng lại gate cũ.

Quyết định và điểm chưa rõ của nguồn: [research note](../docs/research/timeline_sync.md).
Kế hoạch không tự cấp quyền upload hoặc xác nhận tính đúng của model/paper.
Kit, cache, run evidence local, credentials, weights và draft Docker được giữ.

Kiểm chứng local cuối:

- `.tools/uv/uv.exe run --locked python scripts/timeline.py check`: current,
  DOCX hash `b70f5e852b156c7ff0835eebbdd96ccb71b718fd095fd797b554efe5b1837219`.
- `.tools/uv/uv.exe run --locked python scripts/check.py`: exit 0, Ruff/format
  pass, **150 passed in 37.87s**; record và ba log đã đọc tại
  `runs/cpu-check-20261105T092441563393Z-syph2ikl/`. Source không đổi trong gate;
  context báo passed/current, không planning error/warning.
- `P0-SPLIT` ready; P1 blocked bởi P0-GATE, P2 bởi P1, P3 bởi P2; optional skip
  cần lý do. 72 tệp UTF-8/JSON/NFC, 58 local link hợp lệ, `git diff --check` pass.
- 271 hash raw/kit/config/infra/lock/contract/Docker giữ nguyên. Source runtime
  ingestion/profile và các regression cũ giữ nguyên; không có model/PA claim.
- Lượt pytest trực tiếp ban đầu lỗi quyền thư mục TEMP/cache cũ. Cổng chuẩn
  dùng scratch riêng trong workspace và đã pass; không sửa expected hoặc bỏ test.

Đã đồng bộ source migration lên main tại
[e5cac96c149cf18f44ce38f15b4de5e1e6bd9b87](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/commit/e5cac96c149cf18f44ce38f15b4de5e1e6bd9b87).
Remote SHA trùng local. 35 path đã rà, index bytes khớp workspace và không
credential patterns; không có kit/gold/profile/labels/runs/weights được stage.
[GitHub CPU CI 42002438133](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/actions/runs/42002438133)
completed/success: **150 tests trong 10.71s**, Ruff/format pass trên Ubuntu.
Đã đọc steps và log job `127160726014`; bằng chứng JSON lưu local. Commit
state/report sau source chỉ ghi kết quả, không đổi fingerprint CPU hoặc task.
Workspace không còn thay đổi chưa commit sau push cuối.
Evidence local của phiên: `runs/timeline-sync-20261105/` (ignored).
