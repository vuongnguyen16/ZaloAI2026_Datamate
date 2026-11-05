# Setup Archify theo yêu cầu onboarding — 05/11/2026

Phạm vi: cài công cụ có sẵn cho workspace; không thiết kế lại runtime DataMate
hoặc thực hiện P1. Người dùng đã chọn Archify để giúp đồng nghiệp mới hiểu dự án.

Nguồn: [bài tham khảo của người dùng](https://thanhnghiep.top/archify-la-gi-bien-codebase-thanh-so-do-tuong-tac-bang-ai/),
[release v3.2.0](https://github.com/tt-a1i/archify/releases/tag/v3.2.0),
SKILL.md/package.json/LICENSE của commit `208acba8d412335185b2056fedf54b3405df43fb`,
[Codex local skills](https://learn.chatgpt.com/docs/build-skills).
Release stable được GitHub API xác minh ngày 05/11/2026. License release ghim
là MIT; không lấy metadata của main hiện tại để mô tả release này.

Giả thuyết: skill nguyên bản, repo-scoped và runtime Node đi kèm đủ để tạo
HTML local trên Windows, không thêm dependency vào DataMate. Graphify hiện có
đủ hỗ trợ truy vết; facts vẫn phải đối chiếu source/state/contract.

Phương án: cài global bằng npx, cài workspace bằng Skill Installer, hoặc chỉ
dùng Graphify HTML. Chọn installer có `--ref` commit và `--dest .agents/skills`
để tái lập theo repo; không dùng npx hoặc sửa môi trường global. Giữ upstream
nguyên vẹn, thêm provenance riêng. Không bật proactive explainer toàn cục.

Acceptance: Git blobs khớp file cài; registry Codex phát hiện archify enabled,
không load error; doctor pass; demo synthetic render và finalize đủ bốn gate;
CPU gate DataMate pass/current; timeline đồng bộ; runtime/lock/split/kit không
đổi. Artifact chỉ local/ignored, update check tắt khi chạy. Không tạo tài liệu
kiến trúc DataMate trong setup; prompt onboarding được cung cấp để dùng sau.

Các kiểm tra trên không chứng minh chất lượng sơ đồ DataMate, PA, model/GPU,
token savings hoặc review cảm nhận hình ảnh. Reviewer là tác giả.
