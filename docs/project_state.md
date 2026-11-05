# Trạng thái DataMate theo Timeline A–G

Cập nhật 05/11/2026, giờ Việt Nam. Theo yêu cầu người dùng, timeline DOCX trong
Research là nguồn kế hoạch hiện tại; toàn bộ tracker cũ đã được thay thế.
Các mốc ngày trong DOCX là dự kiến, không tự thay lịch/contract BTC.

**Hiện tại:** **A-T2 đã hoàn thiện và done** ở phạm vi format/profile/structure/
descriptor/consumer contract, theo yêu cầu mới sau phản biện Claude. Đã có
runtime BOM/codec/delimiter policy, source-bound overrides, text QA, header/
data-start và data_samples/fallback preview. CPU mới **144 tests pass** sau
fix README NEL/C1, Ruff/format pass; artifact
`runs/cpu-check-20261105T081753167962Z-qao9tpkg/`, source không đổi, đã đọc log.
Final proof `runs/a-t2-completion-20261105/final_acceptance.json` valid=true,
source fingerprint trùng gate hiện hành; raw/cache/source unchanged, 60
business profile/schema repeat hashes giống nhau. Đã đọc source/profile
audits: đủ 339 unit/3.184 cột/3.997.599 hàng/33.628.129 present cells, frame
digests trùng A-T1 trước đổi policy. Spec [hoàn thiện](research/a_t2_completion.md),
[báo cáo](../reports/a_t2_completion_results.md), [runtime policy](runtime_format.md).
Không ghi nhận text flags trong train; không coi đó là chứng minh không có
mọi legacy encoding. Source hoàn thiện đã push theo yêu cầu tiếp theo:
commit [790b1af](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/commit/790b1af1ff48fca7f255206b12a89f02a31b973c),
nhánh main; [source CI 41997216193](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/actions/runs/41997216193)
completed/success, 144 tests trong 12.02s trên Ubuntu, Ruff/format pass.
Đã đối chiếu remote SHA và đọc job steps/log. 26 path đã rà, không secret
patterns hoặc raw/profile/nhãn/runs được stage; kit hash không đổi. Evidence
local: `runs/github-sync-t2-completion-20261105/`; chi tiết
[publication](../reports/github_publish.md). Commit docs sau source chỉ ghi
kết quả; CPU local/final acceptance vẫn cùng fingerprint hiện hành.
Handoff đã xác nhận A-T2 done, CPU passed/current/no warning, frozen
labels/rule và final proof current; kit/cache cũ/protected configs không đổi.
12 tài liệu/tracker UTF-8/NFC/JSON, 53 link local và diff/format pass; evidence
`runs/a-t2-completion-20261105/handoff_verification.json`.

Nhãn source/README đã chốt trước chọn rule, 322 unit, 34 header hai tầng;
group template/file duplicates thành 80 nhóm, dev 103 unit/52 nhóm, check
219 unit/28 nhóm. B2 chọn trước check: 218/219 check tự chọn, 0 sai; còn 1
unresolved. Đây là self-reviewed train structure check (đầu vào từng xem),
không phải independent-human labels, unseen QA holdout hoặc PA. Toàn train
profile hiện hành: 311 auto, 11 unresolved, 17 SQLite schema, không special-case
theo ID. Consumer contract có data-start/header labels; actual prompt/PA
acceptance được giữ tại D-E-T2 và task đó đã thêm dependency A-T2.

Yêu cầu hoàn thiện này thay chỉ định hoãn research trước đó trong phạm vi
header CPU. Converter legacy, multi-region, model/prompt optimization và
cleaner A-T3/T4 chưa mở. A-T1 đã hoàn tất; cache generation mới do code policy
đổi, raw/cache cũ giữ nguyên và 339 frame digests trùng trước/sau.
`G-FOUNDATION`/`A-INVENTORY` vẫn chỉ công nhận phạm vi kế thừa của chúng.

**Đã có:** CPython 3.11.18 + uv 0.13.6 + lock; strict schema/validators;
fake/stub runner, logging/hash; khảo sát sâu train, raw loader/cache và raw
profiler/schema descriptor engineering; CPU gate/CI;
Modal CPU smoke lịch sử. Xem `docs/foundation.md` và
[hướng dẫn loader](ingestion.md), [hướng dẫn profile](profiling.md).
Chưa có real model, scorer, PA/B0.

**Kiểm chứng A-T2 engineering trước hoàn thiện (lịch sử):** CPU gate exit 0, Ruff/format pass, **115 tests
pass trong 27.51s**, không skip; đã đọc JSON/log tại
`runs/cpu-check-20261105T062508275441Z-5p01bmls/`. CPU trước push mới hơn được
ghi ở mục đồng bộ GitHub bên dưới. Full train 30/30 business, 339 unit, 3.184 cột, 3.997.599 hàng,
33.628.129 cell có mặt. Hai lượt profile 151.99s và 152.62s cho hash giống
nhau của toàn bộ 60 business profile/schema JSON. SQL auditor riêng đạt toàn
counts/types/extrema/sample-coordinate/query-schema trong 153.29s; raw 162
file và cache A-T1 60 file không đổi; không parse gold. Source không đổi trong
gate/acceptance, fingerprint trùng nhau. Artifact:
`runs/a-t2-engineering-20261105/acceptance.json`, `audit/verification.json`.
Chi tiết: [kết quả engineering A-T2](../reports/a_t2_engineering_results.md),
[spec](research/a_t2_engineering.md). Self-review, không reviewer thứ hai;
không model/Modal/PA, commit/push/upload hoặc thay dependency/ingest/Docker.
Handoff xác nhận CPU passed/current, không warning; kit train/public/thể lệ
hash không đổi, 7 tài liệu/tracker UTF-8/NFC/JSON và 36 link local hợp lệ,
diff/format pass. Evidence: `runs/a-t2-engineering-20261105/handoff_verification.json`.

Trong increment engineering trước: 322 CSV/XLSX units giữ header unresolved, 17 SQLite dùng declared schema.
Chỉ nhận explicit annotation gắn fingerprint, không tự chọn/fill/ghép header;
codec là cấu hình loader, không coi là detection. Numeric extrema chỉ từ
numeric vật lý; không normalize text money/date/ID hoặc bỏ hàng raw.

**Kiểm chứng A-T1 (lịch sử phiên trước):** CPU gate exit 0, Ruff/format pass, **87 tests
pass trong 15.77s**, không skip; source không đổi trong gate. Artifact:
`runs/cpu-check-20261105T051420112942Z-h48l958o/gate.json`; đã đọc JSON/log.
Full train có 3.997.599 hàng raw (3.997.518 nonempty và 81 hàng trống vật lý),
162 hash raw không đổi. Cold build 374.85s, warm 3.50s với 30/30 cache hits;
đối chiếu nguồn độc lập 339/339 unit pass. Chi tiết và lệnh:
[nghiệm thu loader](../reports/a_t1_loader_results.md),
[spec](research/a_t1_raw_loader.md). Self-review; đối chiếu parser độc lập
không phải review bởi người khác. Không model/Modal/PA, không commit/push.
Lượt cuối sau regression auditor: warm 3.67s/30 hits và full audit 241.32s,
vẫn khớp toàn bộ; `final_acceptance.json` ở
`runs/a-t1-loader-acceptance-20261105T050128Z-j5zoovbj/` có source fingerprint
trùng cổng CPU hiện hành, raw/source không đổi.
Handoff: context A-T1 done, A-T2 todo/ready, CPU passed/current và không
warning; kit hashes train/public/thể lệ không đổi. UTF-8/NFC/JSON, 32 liên
kết local và diff/format pass; `handoff_verification.json` trong cùng run.

**Kiểm chứng phiên reset (lịch sử):** cổng CPU chuẩn exit 0, Ruff/format pass và **59 tests
pass trong 12.07s**; artifact `runs/cpu-check-20261104T164734905777Z-5kmhmukp/gate.json`.
Context A-T1: todo/ready, timeline đúng hash, không có cảnh báo, CPU passed/current;
20 task không lỗi dependency/vòng lặp, ID cũ bị từ chối. Audit kit: hash train/public
và thể lệ giữ nguyên. Skill validator pass. Kết quả ở `reports/timeline_reset_results.md`.
GPU/model không chạy; PA chưa đánh giá. CI GitHub đã pass sau publish, xem phần
đồng bộ bên dưới. Review là self-review.

**Config/tài nguyên:** `configs/smoke.yaml` chỉ synthetic;
`configs/modal_dev.yaml` profile/workspace `vuonghungnguyen07`, tối đa 30 USD
mỗi thí nghiệm. Xác minh lại tài khoản/budget trước job. Không có model đã pin.

**Quy tắc tiếp tục giữ:** raw read-only; không đọc gold vào inference; không
upload BTC data khi chưa rõ quyền; không tuning bằng public/private test;
split/access policy phải rõ trước tuning/huấn luyện; model thật chỉ trên Modal.
Docker nháp giữ nguyên tới bước đóng gói nhóm G sau khi pipeline hoàn chỉnh.

**Handoff tiếp theo:** D-E-T2 nhận schema/header/data-start/preview khi các
model/scorer/split prerequisite của nó sẵn sàng. Actual descriptor-in-prompt
và PA vẫn là acceptance mở tại D-E-T2; không dùng consumer synthetic thay
model. A-T3/T6 vẫn phụ thuộc baseline và E-SPLIT, chưa mở trong phiên này.
Không đọc public/private hoặc gold để chọn rule. Bằng chứng local toàn lượt:
`runs/a-t2-completion-20261105/`.

**Phiên mới:** chạy `uv run --locked python scripts/harness.py context --task A-T2`,
đọc `read_first` và DOCX timeline, review diff rồi chạy CPU gate. Context trả
path/hash timeline; nếu thiếu thì báo thiếu, không hồi sinh plan đã bỏ.

**Backup:** `runs/timeline-reset-backup-20261104-233607/`, 32 file đã xác minh
SHA-256 trước sửa/xóa, local/ignored. Không xóa data, lịch sử Git, runs cũ,
môi trường uv hoặc tài liệu gốc; phiên cleanup không commit/push.

**Đồng bộ GitHub trước phiên hoàn thiện (lịch sử 05/11):** theo yêu cầu người dùng, toàn bộ code,
tests và tài liệu A-T1/A-T2 đã push lên repo public
`vuongnguyen16/ZaloAI2026_Datamate`, nhánh main, source commit `62d67b9`.
Đã đối chiếu remote SHA trùng local; CPU GitHub Actions run `41982405255`
completed/success, 115 tests trong 9.03s trên Ubuntu, lint/format pass. CPU
local mới trước push: 115 passed in 40.07s, lint/format pass; artifact
`runs/cpu-check-20261105T064100622730Z-u8zuplsa/gate.json`, đã đọc JSON/log,
source không đổi/current. Các commit tài liệu sau source commit này chỉ ghi
kết quả publish; không thay implementation. 25 path đã được rà, staged diff,
UTF-8/NFC/JSON, 49 link và credential patterns pass; kit hashes không đổi.
Bản timeline Markdown giữ đủ 137 paragraph/15 bảng/123 dòng bảng và một sơ đồ,
có nguồn/hash DOCX. Dữ liệu BTC, credentials, model, runs và môi trường local
tiếp tục được ignore. A-T2 research vẫn hoãn, không model/PA/Docker. Chi tiết
ở `reports/github_publish.md`, evidence local `runs/github-sync-20261105/`.

**Hiệu đính tài liệu ngày 05/11:** đã rà 15 tệp Markdown, sửa dấu tiếng Việt bị
thay bằng `?` ở tiêu đề/lời dẫn/chú thích ảnh của timeline và tám trường trong
task `G-GITHUB`; hiệu đính câu chữ và khôi phục các cấp tiêu đề. Kiểm tra UTF-8,
Unicode NFC, liên kết nội bộ và JSON đều hợp lệ; 656 đoạn văn gồm nội dung các ô
bảng vẫn khớp DOCX gốc. Code, dữ liệu, luật chấm và các số liệu lịch sử giữ nguyên.
Chi tiết kiểm chứng ở phần hiệu đính trong `reports/github_publish.md`.

Các ghi chú bên dưới lưu diễn biến các đợt trước; trạng thái hiện hành nằm
ở đầu trang và trong backlog.

**Khảo sát train A-T1 ngày 05/11 (trước implementation):** đã đọc đầu vào của 30 business: 107 XLSX
(302 sheet), 20 CSV và 1 SQLite (17 bảng), cùng 30 README, questions/rulebook/
calendar. Không lỗi đọc; 3.997.518 dòng có nội dung **gồm cả header/footer**,
không phải số đơn/giao dịch. Không parse gold; không đọc nội dung public/private.
Hash của 162 file raw giữ nguyên. Đã đối chiếu độc lập số dòng trên 302 sheet/
20 CSV và danh sách file của 30 README; không issue. Phát hiện tiền/ngày trộn
định dạng, nhiều tầng header, dòng tổng và độ hạt khác nhau. Bản chi tiết chỉ
giữ local tại `runs/a-t1-train-survey-20261105/report.md`; note tổng hợp:
[khảo sát A-T1](research/a_t1_train_survey.md). A-T1 in_progress, acceptance
loader/cache còn pending. Toàn train đầu vào đã được khảo sát; ghi nhận mức
truy cập khi thiết kế split trước tuning/huấn luyện.

CPU gate phiên khảo sát: exit 0, Ruff/format pass, 59 tests pass trong 8.87s;
`runs/cpu-check-20261105T025942709843Z-6dd8b3eg/gate.json`, source không đổi
trong gate. Đã đọc JSON/log; đây là kiểm chứng source nền, không phải loader
hay chất lượng model. Review self-review. GPU/Modal model không chạy; PA chưa
đánh giá. Không commit/push hoặc upload dữ liệu.

**Khảo sát sâu train theo yêu cầu bổ sung ngày 05/11:** quét đủ 339 đơn vị
bảng/sheet, 3.184 cột; phân biệt 3.994.970 dòng ứng viên nghiệp vụ với header,
lời dẫn, tổng và 46 ghi chú (chưa dedup). 114.863 dòng ở biz_103/121/122 có
ngữ cảnh nhóm, diễn giải 459.452 ô trong view riêng; raw giữ nguyên. Sales
còn 14.271 lượt keyed lặp sau ngữ cảnh, 16.754 lượt unkeyed phải giữ. 110 kiểm
tra quan hệ không orphan trên khóa không rỗng; join sales/receipts có fanout.
30/30 ngày cuối khớp README; không gap ngày bán trong min–max. 1.095 định nghĩa
quy đổi không có hệ số lỗi/xung đột trên khóa trực tiếp. Có phản chứng gộp
khách theo tên. Số/ngày còn ambiguity có ghi rõ, 38 nhãn status chưa chốt mapping.
Chi tiết: [khảo sát sâu A-T1](research/a_t1_deep_survey.md); report/catalog và
30 hồ sơ business chỉ giữ local ở `runs/a-t1-deep-survey-20261105/`.

Kiểm chứng mới: 38 kiểm tra evidence/parser và validator train pass; 162 hash
raw không đổi. CPU gate exit 0, Ruff/format pass, 59 tests trong 8.47s tại
`runs/cpu-check-20261105T035816552038Z-53d0njvs/gate.json`; đã đọc JSON/log,
source fingerprint giữ nguyên/current. Đây là nghiên cứu đầu vào và regression
nền; chưa loader/cleaner production, GPU/model hoặc PA. Self-review, không
upload/publish. A-T1 tiếp tục in_progress; các module A-T2/T3/T4 chưa nghiệm thu.

Đối chiếu quantity bổ sung: 1.540.167 dòng có đơn vị bán ghi đủ khớp ít nhất
một diễn giải số lượng × hệ số với số lượng cơ bản; 256.087 dòng thiếu đơn vị
bán được tách là chưa kiểm chứng, không quy lỗi data. Nhóm returned được kiểm
tra chéo hai chiều trên 2.736 mã đơn ở tám business; bảng 38 nhãn vẫn là đề
xuất nghiên cứu, chưa cài vào inference/contract.
