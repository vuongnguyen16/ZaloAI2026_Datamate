# Graphify cho Codex trong DataMate

Ngày 05/11/2026. Phạm vi người dùng giao: setup Graphify để giảm đọc lặp
mã nguồn khi làm việc với AI agent. Đây là công cụ phát triển, không mở P1
hoặc thay đổi acceptance P0–P9.

## Nguồn và quyết định

- [Repo chính thức](https://github.com/Graphify-Labs/graphify), README và
  pyproject: package PyPI là `graphifyy`; CLI là `graphify`. Bản khảo sát
  `0.9.102`. AST code chạy local, không embedding hoặc model.
- [Skill Codex upstream](https://github.com/Graphify-Labs/graphify/blob/v8/graphify/skill-codex.md)
  có semantic extraction cho tài liệu và hướng dẫn đa agent. Không dùng nguyên
  khối trong repo này vì phạm vi chỉ code và mục tiêu context gọn.
- [OpenAI Docs về skills](https://developers.openai.com/codex/skills): Codex
  phát hiện `.agents/skills`; chỉ tải nội dung khi cần. Dùng skill repo ngắn
  và hướng dẫn AGENTS, CLI là đường truy vấn chính. Không cần MCP hoặc Cloud.
- [Cấu hình Graphify](https://docs.graphify.com/reference/configuration):
  `GRAPHIFY_BACKEND=none`, `--code-only`, `.graphifyignore` và query budget.

Giả thuyết: graph AST giúp tìm symbol/import/call và phạm vi file với context
ít hơn đọc nhiều file. Graph là chỉ mục dẫn đường, nguồn thực vẫn phải đọc
trước khi sửa. Không suy ra giảm 80% token hoặc PA tốt hơn từ benchmark vendor.

Phương án: (1) skill upstream toàn bộ; (2) MCP/Graphify Cloud;
(3) CLI local + skill repo ngắn + dependency riêng có lock. Chọn (3) để không
đưa dữ liệu ra ngoài, không thêm schema MCP vào context và không đổi dependency
runtime của DataMate. Tool có `pyproject.toml`/`uv.lock` riêng trong
`tools/graphify`; không cài pip vào `.venv` chính.

## Phép thử và acceptance

- Build và update graph local, tắt mọi backend LLM, giới hạn hai worker/CPU
  threads; không cài extras model/PDF/media.
- Chỉ lập chỉ mục code trong `src`, `scripts`, `tests`, `infra`; loại mọi vùng
  khác, secrets, symlink/junction ra ngoài, dữ liệu BTC/gold/runs và môi trường.
- Chạy query/explain/path thật; kiểm source của graph nằm trong phạm vi.
- Thử truy vấn giới hạn context; budget Graphify là ước lượng, không phải giới
  hạn billing. Chưa có đo A/B token thực trên các phiên Codex.
- Skill validate, timeline check và CPU gate cuối phải pass; ghi evidence local,
  cập nhật state/backlog mà giữ lộ trình hiện tại.

Review do tác giả thực hiện. Graph/query/artifact giữ local và ignored;
không dùng graph làm quyền truy cập gold hoặc thay scoped reader/evaluator.
