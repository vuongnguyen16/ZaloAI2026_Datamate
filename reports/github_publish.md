# Đồng bộ GitHub để đọc/review trên web

Ngày 04/11/2026, giờ Việt Nam. Người dùng yêu cầu upload repo hiện tại để AI web
dễ đọc. Đã publish source, config, tests, tài liệu và timeline vào repo public
[vuongnguyen16/ZaloAI2026_Datamate](https://github.com/vuongnguyen16/ZaloAI2026_Datamate),
nhánh main; giữ nguyên visibility đang có, không thay cấu hình quyền repo.

## Phiên bản và bằng chứng

- Source commit đã push và đối chiếu SHA remote/local:
  [`c69d4da0952d9ea8acf96f87f841071b8f0f806d`](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/commit/c69d4da0952d9ea8acf96f87f841071b8f0f806d).
- Cổng CPU local trước push: `.tools/uv/uv.exe run --locked python scripts/check.py`,
  exit 0; Ruff/format pass, **59 passed in 7.49s**. Artifact local ignored:
  `runs/cpu-check-20261104T165544622253Z-oze3s9zf/gate.json`.
- [GitHub Actions CPU run 41872674037](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/actions/runs/41872674037):
  completed/success cho đúng source SHA. Đây là bằng chứng CI riêng, không suy từ local.
- Cây source ban đầu 57 file đã được rà soát trước push; không có path raw kit,
  model, runs, môi trường hoặc credential. Kiểm tra credential patterns và các
  path trong lịch sử local không phát hiện mục bị cấm; không in token/secret.
- `git diff --cached --check` pass. Git push thành công, main tracking origin/main;
  không force push, thay remote hoặc viết lại lịch sử.

## Bản đọc web

`Research/Timeline_DataMate_A-G.md` là bản đọc sinh từ DOCX gốc, giữ nguồn và
SHA-256. Đã đối chiếu mọi paragraph/cell text: 137 paragraph, 15 bảng với 123
dòng bảng. Sơ đồ PNG trích nguyên byte tại `Research/timeline_assets/image1.png`.
DOCX giữ nguyên và tiếp tục là nguồn kế hoạch, Markdown không tạo roadmap khác.
README dẫn rõ timeline → state → backlog → contract cho việc đọc/review trên web.

## Phạm vi

Dữ liệu BTC/thể lệ gốc, credentials, model, venv/caches, run artifacts và backup
cleanup tiếp tục local/ignored theo policy đã có; không force-add để upload chúng.
Fixture synthetic, contract/provenance/hash metadata được giữ trong source.
Không chạy Modal/GPU/model, không đo PA hoặc build/test Docker trong phiên đồng bộ GitHub.
Tài liệu này ghi lại source commit đã kiểm chứng; các commit tài liệu sau đó có
thể cập nhật main mà không thay kết quả kiểm chứng của source commit này.

## Hiệu đính tiếng Việt ngày 05/11/2026

Đã phát hiện bước tạo Markdown qua pipeline PowerShell làm mất dấu trong các
chuỗi tự viết: tiêu đề, lời dẫn và chú thích ảnh. Phần văn bản trích trực tiếp từ
DOCX vẫn nguyên vẹn. Tám trường tiếng Việt của task `G-GITHUB` được tạo cùng cách
cũng gặp lỗi này. Bản rà soát trước chỉ đối chiếu nội dung trích nguồn nên đã bỏ
sót các đoạn tự viết; không dùng kết quả đó để khẳng định toàn bộ bản Markdown
trước hiệu đính không có lỗi.

Đã sửa trực tiếp bằng UTF-8, hiệu đính câu chữ trong tài liệu và khôi phục các
cấp tiêu đề của timeline. Kết quả rà soát:

- 15 tệp Markdown được đọc và kiểm tra UTF-8, Unicode NFC và liên kết nội bộ.
- Toàn bộ file văn bản tracked không còn dấu hiệu ký tự hỏng đã phát hiện.
- 656 đoạn văn, bao gồm nội dung các ô bảng, vẫn khớp DOCX; đủ bảy nhóm A–G và
  24 tiêu đề con. Tiêu đề chính trùng lặp đã được bỏ.
- DOCX gốc và sơ đồ giữ nguyên; JSON backlog hợp lệ. Các task chức năng, code,
  dữ liệu, luật chấm và số liệu kiểm chứng lịch sử không thay đổi.
- `git diff --check` pass. Phiên hiệu đính kiểm tra nội dung tài liệu, không tạo
  thêm test mô phỏng câu chữ hoặc chạy model/GPU/evaluation.

Bằng chứng kiểm tra cục bộ: `runs/editorial-review-20261105.json` (ignored).
