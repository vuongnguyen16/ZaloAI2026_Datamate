# Sửa ngôn ngữ Archify — 05/11/2026

Theo yêu cầu người dùng, Archify workspace chỉ tạo nội dung tiếng Anh hoặc
tiếng Việt; nút giao diện cố định dùng tiếng Anh. Không cài catalog UI tiếng
Việt mới. Runtime gốc có catalog đa ngôn ngữ nhưng skill không chọn chúng.

Nguyên nhân được tái hiện: `explainer/render.mjs` mặc định `zh-CN` khi draft
thiếu locale. Do đó nội dung tiếng Việt vẫn có menu/footer tiếng Trung.
Skill chính còn có trigger và câu mẫu tiếng Trung dễ được chép vào output.

Đã đổi fallback renderer thành `en`; thêm quy tắc Anh/Việt và yêu cầu
`meta.locale=en` vào skill. Đã thay câu mẫu trong skill và các hướng dẫn
authoring chính bằng Anh/Việt. Các chức năng và template khác giữ nguyên.
Provenance không còn tuyên bố nguyên bản: 4 file upstream sửa local, 1 test
thêm mới; 199 file upstream khác khớp hash ban đầu, license/notices không đổi.
[UPSTREAM.json](../.agents/skills/archify/UPSTREAM.json) giữ hash upstream và
hash patch riêng; phải review/áp lại patch khi nâng cấp.

## Kiểm chứng

- `node --test .agents/skills/archify/tests/language-default.test.mjs`: trước
  sửa 2/2 fail đúng lỗi `zh-CN` thay vì `en`; sau sửa 2/2 pass. Test render
  HTML thật từ draft Anh/Việt thiếu locale, kiểm nội dung và các nhãn/menu.
- `quick_validate.py .agents/skills/archify`: skill valid.
- Doctor và Node syntax check renderer/test: pass.
- Trang onboarding hiện có đã render lại với `@meta locale=en`; finalize đủ
  validate/deliver/check/browser-check pass, 0 diagnostic.
- Đã kiểm chữ body của browser, markup hiển thị và menu words không có chữ
  Trung. Catalog/chuỗi fallback ẩn trong script không phải nội dung hiển thị.
  Kết quả đếm ở `runs/archify-language-20261105/acceptance.json`.

Evidence local: `runs/archify-language-20261105/`, receipt trang onboarding ở
`.archify/explainer-datamate-onboarding-20261105-220839/review-language-20261105/`.
Chỉ kiểm tự động, không claim review cảm nhận hình ảnh. Test Node chạy riêng,
không thêm Node thành dependency runtime DataMate hoặc CPU CI Python.

Không sửa code inference/evaluator, không đọc kit/gold, không gọi Modal/model,
không PA/B0 claim. Backlog chỉ cập nhật development_tooling; P1 vẫn todo.
CPU cuối: **238 passed in 127.90s (0:02:07)**, Ruff lint/format pass, exit0;
`runs/cpu-check-20261105T152236134716Z-x5pxobyq/gate.json`. Đã đọc đủ JSON/ba log,
source không đổi trong gate. Context P1 passed/current, ready, không warning.
Chưa commit/push. Các kiểm ngôn ngữ chứng minh renderer và artifact kiểm thử;
không phải cam kết hành vi mọi lần chạy LLM. Skill bắt buộc kiểm bản sinh ra.
