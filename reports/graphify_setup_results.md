# Kết quả setup Graphify cho Codex

Ngày 05/11/2026, giờ Việt Nam. Scope: công cụ phát triển theo yêu cầu người dùng;
P0/G0 giữ done, P1 vẫn todo/ready, không có job Modal hoặc thay đổi acceptance.

## Kết quả

- Graphify `0.9.102` (`graphifyy`) trong `tools/graphify/.venv`, dependency/lock
  riêng. Runtime pyproject/lock DataMate không đổi.
- Graph local: 49 file Python, 566 node,
  1921 cạnh. Code trong src/scripts/tests/infra; docs/fixtures,
  data/gold/runs/credentials và vùng gốc mới bị loại. Backend LLM `none`,
  query log global tắt; không cài extras model/embedding/CUDA.
- Build/update/query/explain/path/HTML exit0. Update không đổi code dùng lại
  49 file, 0 re-extracted. Path thật `run_eval() → score()` là cạnh calls;
  query trả vị trí source, budget mặc định 1200/depth1, có cảnh báo truncation.
- Fixture synthetic kiểm ignore bằng package thật: chỉ src/module.py và
  scripts/tool.py được nhận; data/gold.py, gold.jsonl, runs, thư mục private mới,
  credentials.py và JSON fixture đều bị loại.
- Skill `$graphify` ngắn trong `.agents/skills`, validator pass; AGENTS hướng
  dẫn graph trước tra cứu kiến trúc rộng. Wrapper từ chối graph stale hoặc
  source ngoài scope; tool config/lock đã vào CPU fingerprint.

## Kiểm chứng

Lệnh CPU: `.tools/uv/uv.exe run --locked python scripts/check.py` với cache
theo README. 238 passed in 44.39s; Ruff check/format pass, source không đổi trong gate.
Gate hiện hành: `runs/cpu-check-20261105T125449495803Z-h34xb6o4/gate.json`. Đã đọc JSON và cả ba stage log;
context P1 passed/current, ready, không warning/planning error.
Timeline check current, DOCX SHA-256 vẫn
`b70f5e852b156c7ff0835eebbdd96ccb71b718fd095fd797b554efe5b1837219`.

Sáu unit tests mới kiểm source boundary, config fingerprint, stale khi sửa/xóa,
graph ngoài scope và backend/logging; không cần cài Graphify trong runtime CPU.
Lần gọi pytest trực tiếp đầu tiên lỗi quyền thư mục TEMP của máy; chạy lại với
scratch trong runs pass6/6. Cổng CPU dùng scratch riêng và pass đầy đủ.

Evidence tool local: `runs/graphify-setup-20261105/`, receipt trong
`graphify-out/datamate_receipt.json`; JSON graph/cache/HTML đều ignored.
Review do tác giả thực hiện. Không commit/push/upload dữ liệu BTC.

## Giới hạn và bàn giao

Chưa đo A/B token thực của Codex; không cam kết mức giảm 80% từ quảng cáo.
Build AST không dùng LLM token, query output vẫn vào context. Graph có thể
thiếu dynamic dispatch; cần đọc source và dùng rg nếu recall thiếu.
CPU/tooling pass không phải model/PA/B0, không thay scoped gold policy.
Hướng dẫn: [docs/graphify.md](../docs/graphify.md).
