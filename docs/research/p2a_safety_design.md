# P2a lưới an toàn và bảng chéo taxonomy

Ngày06/11/2026. Người dùng yêu cầu bắt đầu ngay P2a và bảng chéo taxonomy
theo bản sửa đã gửi; thực hiện inline trong workspace, không mở lại vòng hỏi
thiết kế. Nguồn: timeline/backlog P2, quyết định G2/G5, contracts/scoring,
runner hiện tại và hai bản plan/phản biện người dùng cung cấp trong phiên.
G5 giữ nguyên; câu hỏi trước nói về dung sai cụm, không phải điểm từng câu.

## Phạm vi và lựa chọn

Increment này chỉ làm CPU safety và bảng chéo dev. Chưa model adapter,
prompt/probe, cleaner/domain_lib, PA hoặc G2. predict mới có backend
safe_abstain thật, ghi rõ no_model; fake chỉ trong fixture synthetic.
Không thay run_smoke/run_stub hoặc scorer policy/split/access đã khóa.

Chọn JSON serializer nhỏ dùng Decimal chính xác, thay vì float/string hoặc
thêm dependency. Submission chấp nhận Decimal hữu hạn có bounds giống scorer;
JSON number viết dạng thập phân không số mũ. Dòng bytes cuối được parse và
validate bằng scorer (prediction-only), không gọi score/gold trong inference.
Percent quantize2 HALF_UP; number không tự làm tròn. Cũ int/float vẫn hợp lệ.

Chọn hard-link publication no-clobber: temp mới cùng thư mục, fsync file,
os.link tới đích, bỏ temp, sync directory trên POSIX. Đích cùng bytes/hash
dùng lại; khác thì giữ cả hai và báo conflict. Không fallback os.replace.
Đích xuất hiện trong lúc publish cũng phải xử lý như vậy. Không follow
symlink/reparse path; file cũ không bị sửa. Chỉ file tạm do lần publish đó
tạo mới được unlink, không dọn file của người dùng.

Windows không có portable directory fsync trong os; khả năng này phải ghi
rõ là unavailable, bảo đảm thử là process-crash recovery, không claim
power-loss durability. Linux dùng fsync directory; filesystem/mount thực
tế /result và hard-link support phải kiểm tại P3. Không giả vờ fsync thành
công trên Windows, cũng không ghi đè để né lỗi filesystem.

Checkpoint mỗi invocation một segment O_EXCL riêng, append+flush+fsync từng
dòng; giữ nguyên segment cũ. Resume phải có identity khớp: input inventory,
config, code và model revision (no_model ở P2a). Manifest immutable, một
writer lock hệ điều hành cho mỗi output; lock tự nhả khi process bị kill.
Không xóa lock file để tránh race inode. Kết quả/metadata chỉ finalize khi
không còn writer cũ; output lạ hoặc fingerprint khác bị từ chối trước ghi.
Khởi tạo dùng marker rỗng mang SHA identity trước publish manifest rồi mới
tạo lock; marker/pending đúng namespace cho phép resume nếu chết trước manifest.
File lạ vẫn giữ nguyên và bị từ chối; không xóa pending cũ khi phục hồi.

Chỉ dùng dòng checkpoint có newline và parse/shape/envelope hợp lệ. Tail
chưa newline được ghi chẩn đoán và xử lý lại; không sửa/truncate segment.
Dòng complete hỏng được log/recompute nếu ID biết; không che corruption như
run sạch. Record trùng cùng payload kết quả gộp; khác nhau → abstain/log.
Kết quả serializer được lưu trong checkpoint, Decimal không qua float.

Input parser riêng cho predict: giới hạn bytes/dòng/số ID, strict JSON keys
và UTF-8. JSON hợp lệ nhưng sai question schema còn ID rõ → abstain; JSON
không route được ID → data error, không đoán bằng regex. ID trùng identical
gộp, khác payload → abstain; các ID khác tiếp tục. Tập ID được xác định trước
khi gọi backend, không đọc answers.jsonl. Nếu input scan hết giờ/bị kill,
không claim đã biết toàn bộ ID; resume hoàn tất scan rồi xuất đủ ID hợp lệ.

Runner dùng lô hữu hạn, checkpoint ngay từng câu; mọi exception/backend
timeout chuyển phần còn lại sang abstain và finalize. Timer tính từ entry
application trước nạp dữ liệu; dành reserve cho output. Stop/kill rồi resume
cùng identity phải ra đúng một dòng/ID, không ghi đè final cũ. Final đã có mà
khác kết quả mới là conflict, không âm thầm thay output.

DuckDB worker CPU riêng cho trusted queries của domain code, không là SQL
fallback/CLI chạy SQL của model. Read-only DB, external access tắt, threads2,
memory256MiB, bounded result. Parent yêu cầu interrupt qua control pipe tới
thread giữ connection, rồi terminate/kill nếu không dừng. Mọi đường phải join
và báo cleanup; timeout bao gồm startup. Không coi DuckDB setting là OS ACL.
Worker trả exact JSON bytes, không pickle object kết quả; thread nhận/parse được
supervisor tính trong timeout. Kill/join đóng đầu pipe khi receive dở.
Output retained tối đa128MiB, reserve bytes cho abstain còn lại, finalize stream;
journal tối đa512MiB/100000records/10000segments và đọc streaming có bounds.
Default6giờ/reserve120giây/per-question30giây khớp configs/predict.yaml.
Load/finalize có giới hạn dữ liệu; đây chưa phải OS hard real-time deadline
trên storage treo. P3 phải đo headroom runtime thực trước đóng gói.

## Taxonomy dev

Không mở lại gold. Dùng đúng artifact taxonomy P0 đã pin trong
manifests/p0_evidence.json: authorize context dev trước, kiểm blob SHA trước
JSON decode, kiểm split/rules/implementation và membership dev. CLI không
cho truyền arbitrary metadata/gold file làm taxonomy. Cross module riêng
giữ source classifier P0 không đổi. Thử nghiệm chỉ dùng synthetic evidence.

Cross family×operation×expected_type×time_form: family là primary heuristic;
operations/time_forms đa nhãn tạo Cartesian memberships. Báo n câu unique và
membership count riêng, không coi tổng ô là số câu. Không xuất question text,
answers/alias hoặc IDs trong bảng chéo. Artifact/cell counts giữ local runs;
repo chỉ pointer/hash/summary đã được phép, không tự publish dữ liệu BTC.

## Bằng chứng và ranh giới

TDD cho numeric round-trip/9type, no-clobber races, torn journal, duplicate
conflicts, fingerprint mismatch, worker timeout/cleanup, process kill/resume,
deadline/input errors và taxonomy scope/hash/multi-label. Giữ test cũ.
CPU gate sau source cuối; review độc lập một lần toàn branch, fix có regression.
Task P2 là in_progress duy nhất, P2a done không đồng nghĩa G2/P2 done.
Không gọi cloud, không tải weights hoặc cài dependency GPU local.
