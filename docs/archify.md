# Archify cho onboarding DataMate

Archify **3.2.0** được cài theo workspace tại `.agents/skills/archify/`,
ghim commit `208acba8d412335185b2056fedf54b3405df43fb` của
[repo chính thức](https://github.com/tt-a1i/archify/tree/208acba8d412335185b2056fedf54b3405df43fb).
Có patch local giới hạn nội dung Anh/Việt và sửa default explainer từ tiếng
Trung sang tiếng Anh; MIT và third-party notices giữ nguyên. Không cần npm
install, API key hoặc dịch vụ vẽ sơ đồ.

## Ngôn ngữ

Nội dung theo yêu cầu tiếng Việt hoặc tiếng Anh; giao diện cố định dùng tiếng
Anh. Skill yêu cầu `meta.locale: "en"` hoặc `@meta locale=en`, không chọn locale
Trung và kiểm nội dung trước khi giao. Catalog đa ngôn ngữ upstream vẫn nằm
trong package nhưng không dùng cho output của workspace. Chưa có catalog UI
tiếng Việt đã review. Khi cập nhật upstream, phải giữ hoặc áp dụng lại patch
local trong provenance và chạy regression test ngôn ngữ.

## Dùng trong Codex

Từ lượt tiếp theo có thể gọi `$archify`. Nếu catalog chưa hiện, mở lại phiên
Codex ở workspace này. Skill nằm trong repo; không cài global.

Prompt để tạo tài liệu cho đồng nghiệp mới:

```text
$archify Hãy tạo một trang onboarding DataMate bằng tiếng Việt cho đồng nghiệp
mới. Đọc context DataMate và timeline hiện hành trước; dùng Graphify truy vết
code rồi đọc source để kiểm chứng. Giải thích mục tiêu dự án, các thành phần
đã có, luồng ingest → profile và luồng đánh giá scoped, cùng thứ tự đọc code.
Phân biệt rõ phần đã triển khai với kiến trúc mục tiêu P1–P9; dẫn file và dòng
source cho các khẳng định về code. Chỉ dùng code và tài liệu project được phép;
không đọc data, gold, membership, artifact BTC trong runs hoặc credentials.
Xuất HTML độc lập trong .archify/, không publish hoặc upload.
```

Để đào sâu một luồng:

```text
$archify Vẽ sơ đồ kiến trúc hiện có của run_eval → read_scoped → score cho
người mới. Dùng Graphify và kiểm source; thể hiện ranh giới inference/evaluator,
policy và audit. Không đọc gold hoặc artifact BTC. Xuất HTML local có source
evidence, phân biệt policy provisional với luật đã có nguồn.
```

Graphify tìm quan hệ code; Archify trình bày phần đã kiểm chứng thành sơ đồ
hoặc trang giải thích. Timeline chỉ mô tả công việc, không chứng minh module
đã tồn tại. State/backlog tiếp tục là tracker duy nhất. Setup không mở P1 hoặc
đổi trạng thái acceptance P0/model/PA.

## Chạy và kiểm tra môi trường

Từ thư mục gốc workspace:

```powershell
$env:ARCHIFY_UPDATE_CHECK_DISABLED = '1'
node .agents/skills/archify/bin/archify.mjs doctor
node .agents/skills/archify/bin/archify.mjs demo .archify/my-demo
```

Biến trên áp dụng cho tiến trình hiện tại và tiến trình con; đặt lại trong
terminal mới. AGENTS yêu cầu đặt biến trước các lệnh Archify để tắt update
check. Không sửa config global. Browser gate dùng Chrome/Chromium hoặc Edge
có sẵn; máy chưa có browser cần cài browser hoặc đặt `ARCHIFY_CHROME` tới
executable có sẵn. Doctor không tự chứng minh browser gate đã chạy.

Khi tạo diagram thật, agent đọc skill và các reference liên quan, viết candidate
có source evidence rồi chạy `finalize` với `--repo-root .`. Kiểm tra tự động
và review bằng mắt là hai loại bằng chứng khác nhau. Nội dung nhãn/tiêu đề/
chú thích tiếng Việt phải UTF-8 và được kiểm sau render.

Candidate, HTML và receipt ở `.archify/<type>-<slug>-<timestamp>/`, đã gitignore.
Chỉ chia sẻ HTML sau khi review nội dung/quyền chia sẻ; file có thể nhúng
source excerpt. Người nhận mở HTML bằng browser, không cần cài Archify.

## Cài lại và nâng cấp

Clone workspace có thư mục skill là dùng được với Node >=18. Không chạy các
script npm dành cho phát triển upstream để dùng skill. Nếu thư mục bị thiếu,
dùng Skill Installer với repo `tt-a1i/archify`, path `archify`, ref commit trên
và dest `.agents/skills`. Installer từ chối ghi đè thư mục đã có.
Chỉ nâng phiên bản khi có yêu cầu; review thay đổi, license và chạy lại kiểm tra.

[Quyết định setup](research/archify_setup.md),
[kết quả kiểm chứng](../reports/archify_setup_results.md),
[provenance](../.agents/skills/archify/UPSTREAM.json).
