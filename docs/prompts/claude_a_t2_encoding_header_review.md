Tôi muốn bạn phản biện độc lập phần **dò encoding và tìm header trong A-T2** của dự án DataMate. Tôi đã kết nối GitHub repository với Claude để bạn đọc trực tiếp code và tài liệu.

Đây là yêu cầu **đọc repo, phân tích và đề xuất phạm vi nghiên cứu**, chưa phải giao triển khai. Không sửa code/tracker, tạo PR, chạy model, huấn luyện, gọi dịch vụ trả phí hoặc tự thực hiện một đợt deep research lớn.

Hai câu hỏi trọng tâm:

1. Với tình trạng thực tế của project, phần nào chỉ cần engineering, phần nào cần kiểm chứng thực nghiệm, phần nào thực sự cần research? Có phần nào đã bị gọi là research quá rộng hoặc chưa cần làm không?
2. **"research" ở phần này cần làm những cái gì?** Hãy cụ thể đến từng câu hỏi cần giải đáp, giả thuyết, phương án đối chứng, dữ liệu, phép thử, tiêu chí đạt/dừng và artifact bàn giao.

Đừng mặc định quan điểm của coding assistant trước đó là đúng. Tôi cần ý kiến độc lập, có căn cứ từ repo, với mức đầu tư phù hợp cho một project thi đấu.

## 1. Repository và cách đọc context

- Repo: https://github.com/vuongnguyen16/ZaloAI2026_Datamate
- Đọc nhánh `main` đang truy cập được; báo rõ branch/commit nếu connector cung cấp. Nếu không biết SHA, nói rõ, không tự đoán.
- Mốc source A-T1/A-T2 đã công bố: `62d67b9c97b1f3722ca5339412f2125347c44696`. Main có thể có commit tài liệu mới hơn; không nhầm lịch sử trước implementation với trạng thái hiện tại.
- Nguồn kế hoạch là `Research/Timeline DataMate theo nhóm việc A–G.docx`. Bản đọc web tương ứng: `Research/Timeline_DataMate_A-G.md`, đọc phần A, nhất là T1–T4. DOCX hash: `e74b1292119f01ca3eae7d20d709921219efc30e655e01909685c50d5363eb51`.
- Ngày/mốc trong timeline là dự kiến; không dùng chúng như lịch thi chính thức hoặc bằng chứng một module đã có.

Đọc theo thứ tự sau, ưu tiên những đoạn liên quan nếu giới hạn context:

**Trạng thái và contract:**

- `README.md`
- `AGENTS.md`
- `docs/project_state.md`
- `tasks/backlog.json`: A-T1, A-T2, E-SPLIT, D-E-T2, A-T3-T6
- `docs/requirements.md`
- `manifests/competition_contract.json`
- `Research/Timeline_DataMate_A-G.md`, phần A.

**Khảo sát, thiết kế và kết quả:**

- `docs/research/a_t1_train_survey.md`
- `docs/research/a_t1_deep_survey.md`
- `docs/research/a_t1_raw_loader.md`
- `docs/research/a_t2_engineering.md`
- `docs/ingestion.md`
- `docs/profiling.md`
- `reports/a_t1_loader_results.md`
- `reports/a_t2_engineering_results.md`
- `reports/github_publish.md` nếu cần phân biệt source/CI đã publish với artifact local.

**Code và tests cần đối chiếu khi đưa nhận xét kỹ thuật:**

- `src/datamate/ingest/model.py`, `readers.py`, `loader.py`
- `src/datamate/profile/model.py`, `engine.py`, `stats.py`
- `tests/integration/test_ingest.py`
- `tests/integration/test_profile.py`
- `scripts/verify_ingest.py`
- `scripts/verify_profile.py`

Không chỉ đọc README rồi suy đoán implementation. Với nhận xét quan trọng, dẫn path và function/section hoặc line nếu lấy được. Phân biệt: điều trực tiếp thấy trong code; điều báo cáo local ghi nhận; giả thuyết của bạn; bằng chứng còn thiếu.

**Giới hạn truy cập:** raw BTC, gold, cache DuckDB, các profile chứa mẫu và `runs/` giữ local/ignored, không có trong GitHub. Không tuyên bố đã đọc/chạy/kiểm chứng chúng. Các số liệu bên dưới là kết quả được báo cáo trong repo, không thay thế quyền truy cập dữ liệu gốc. Nếu một file thực sự không truy cập được, báo rõ rồi tiếp tục với context hiện có; không coi việc không thấy raw trên GitHub là lỗi đồng bộ cần upload dữ liệu.

## 2. Bối cảnh và mục tiêu thực tế

DataMate là pipeline trả lời câu hỏi tiếng Việt trên dữ liệu kinh doanh không đồng nhất của từng business. Input có CSV/XLSX/SQLite, README theo business, cùng questions/rulebook/calendar cấp split. Hướng phát triển là dùng schema profile để baseline/agent hiểu bảng/cột và truy vấn SQL đúng.

Hiện chưa có scorer thực, model thật, PA hoặc baseline end-to-end đã nghiệm thu. BTC không cung cấp executable runner/evaluator theo xác nhận của chủ project; nhóm E sẽ xây scorer từ đặc tả. Vì vậy không thể lấy test CPU hoặc consumer synthetic làm bằng chứng chất lượng trả lời câu hỏi.

Trình tự đã làm:

1. Khảo sát kỹ train ở A-T1, lưu ghi chép và bằng chứng.
2. Triển khai, nghiệm thu loader raw CSV/XLSX/SQLite → DuckDB, cache theo business.
3. Tôi chỉ giao phần engineering của A-T2; coding assistant đã hoàn thành profile raw và schema descriptor, hoãn tự dò encoding/header và các quyết định nghiên cứu.
4. Tôi hỏi vì sao dò encoding/header cần nghiên cứu, và giờ muốn bạn kiểm tra lại cách phân chia đó.

Trạng thái tracker: A-T1 `done`; A-T2 `in_progress`, `engineering_status=done`, `research_status=deferred_by_user`. Việc tôi xin tư vấn lần này cho phép bạn phân tích và thiết kế nghiên cứu cần thiết, không phải tự mở implementation hoặc thay trạng thái task.

## 3. Dữ liệu đã quan sát và điều chưa được chứng minh

Theo báo cáo khảo sát train:

- 30 business, 3.000 câu hỏi; 162 file raw.
- 128 file bảng: 107 XLSX, 20 CSV, 1 SQLite.
- 339 đơn vị nguồn: 302 worksheet, 20 CSV, 17 bảng SQLite.
- 3.184 cột tính theo từng đơn vị nguồn.
- 3.997.599 hàng raw vật lý, gồm 3.997.518 hàng có nội dung và 81 hàng trống hiện diện rõ trong XML. Đây không phải số đơn/giao dịch.
- **20 CSV đều đọc được strict UTF-8 có BOM, delimiter dấu phẩy; chưa có bằng chứng TCVN3/VNI trong các CSV train này.** Không được suy từ timeline có nhắc TCVN3/VNI thành train đang có chúng.
- Theo khảo sát A-T1, header của 322 CSV/sheet nằm ở dòng 1/2/3/4 lần lượt 207/34/42/39; SQLite có 17 schema khai báo. Đây là kết quả khảo sát được ghi nhận, chưa phải một detector production đã được đánh giá độc lập.
- Có lời dẫn, cấu trúc header nhiều tầng, dòng tổng, ghi chú, bảng chia file/sheet, ngữ cảnh nhóm và độ hạt khác nhau.
- Không quan sát sheet ẩn, ô gộp, formula hoặc ô lỗi Excel trong khảo sát train ban đầu. Loader/tests có hỗ trợ nhiều trường hợp như vậy, nhưng **fixture hỗ trợ không chứng minh chúng đã xuất hiện trong train**.
- Có file bảng trùng byte giữa một số nguồn. Không tự suy ra business trùng nhau; cần lưu ý nguy cơ leakage khi chia tập theo file/business.
- Toàn train đầu vào đã được khảo sát trước đây. Split/access policy E-SPLIT chưa khóa; không gọi một phần train đã quan sát là holdout hoàn toàn chưa đụng tới.

Chưa có bằng chứng độ chính xác của detector encoding/header trên nguồn chưa biết, chưa đo lỗi downstream của các quyết định header, và chưa có PA baseline. Các giả thuyết parsing số/ngày/status trong khảo sát cũ chưa phải contract cleaning đã xác nhận.

## 4. Implementation hiện tại và những gì có thể tận dụng

### A-T1: lớp raw

- Mỗi business có một DuckDB; mỗi CSV/sheet/bảng SQLite có storage riêng và view `raw_<hash>`.
- Cột dữ liệu theo vị trí `c0001`… với SQL type VARCHAR/NULL; giữ `__row`, `__width`, metadata và định danh nguồn.
- CSV giữ text/leading zero/whitespace; codec/delimiter explicit, mặc định UTF-8-sig/comma. Không dò bằng `errors=replace`.
- XLSX đọc OOXML streaming, giữ giá trị/lexeme, kiểu vật lý, tọa độ, sparse/blank cells, style reference, workbook epoch, formula/cached value và metadata cấu trúc cần thiết. Không tính formula.
- SQLite dùng snapshot readonly; giữ declared columns/schema và kiểu vật lý, không chạy DDL/view từ data.
- Giữ header/lời dẫn/tổng/ghi chú/trùng/trống. Không tự chọn header, fill nhóm, chuẩn hóa tiền/ngày, dedup hoặc gộp bảng.
- Cache fingerprint gồm nguồn, cấu hình, code/runtime; kiểm hash/catalog/frame integrity. Source gốc và cache được bảo toàn.

### A-T2: engineering profile

- Quét đầy đủ từng unit, phân biệt present/missing/NULL/empty/nonempty, histogram physical types, ratios, length và lexical extrema.
- Numeric extrema chỉ từ numeric vật lý XLSX/SQLite, không ép text money/date/ID thành số; serial Excel vẫn là số.
- Mẫu là 3 giá trị nonempty distinct đầu tiên theo source row, không phải representative sampling đã nghiên cứu.
- Preview mặc định 6 hàng vật lý đầu, tối đa 32 cột, 256 byte UTF-8/value; phần cắt có metadata/hash. Có options điều chỉnh trong giới hạn. Phân biệt số dòng nguồn với thứ tự các hàng XML thực sự có mặt.
- SQLite header status `source_schema`. CSV/XLSX mặc định `unresolved`, có row preview và metadata nguồn.
- Có `--header-map`: annotation tường minh theo business/file/unit, gắn ingest fingerprint; có thể chỉ định nhiều hàng header. Giữ evidence missing/NULL/empty/trùng, không fill merged cells, không tạo SQL alias từ label và không loại hàng khỏi thống kê.
- `explicit_annotation` chỉ có nghĩa là đã nhận khai báo, không chứng minh khai báo đúng. Hiện chưa tạo bộ annotation header BTC để đưa vào production.
- Codec/delimiter trong profile là cấu hình loader, không được trình bày như encoding đã được phát hiện hay văn bản được xác nhận đúng nghĩa.
- Xuất profile JSON và schema descriptor có tên view/cột SQL thật, labels/samples/provenance; consumer synthetic truy vấn được. Chưa có prompt baseline thật.

Theo nghiệm thu: hai lượt profile đủ 30 business/339 unit/3.184 cột/3.997.599 hàng/33.628.129 ô có mặt, mỗi lượt khoảng 152 giây; 60 business profile/schema JSON có hash giống nhau. Auditor riêng đối chiếu counts/types/extrema/sample-coordinate/schema, raw/cache không đổi. Bộ CPU có 115 tests pass và CI CPU đã được ghi trong báo cáo publish. Những điều này chứng minh các kiểm tra engineering đã chạy, **không chứng minh tự dò encoding/header hay prompt/PA tốt**.

## 5. Quan điểm đang cần bạn phản biện

Coding assistant giải thích rằng:

- Đọc theo codec biết trước, xử lý BOM, decode strict, báo lỗi và dùng header đã khai báo là engineering.
- Tự chọn codec/header khi nhiều cách diễn giải hợp lý, thiết kế confidence/fallback và kiểm tính tổng quát có thể cần nghiên cứu thực nghiệm.
- Research không nhất thiết là đọc paper hoặc huấn luyện model; có thể chỉ là đặt giả thuyết, so phương án và đo lỗi.

Tôi muốn bạn kiểm tra cả ba ý đó. Đừng kết luận cần research chỉ vì có ambiguity, cũng đừng kết luận chỉ cần thư viện vì đã có API. Hãy phân biệt:

1. Engineering với quy tắc/spec đã rõ.
2. Kiểm thử/validation thông thường.
3. Nghiên cứu thực nghiệm để chọn giữa các phương án chưa rõ.
4. Literature review hoặc model research có thực sự cần không.
5. Hạng mục chưa có bằng chứng cần làm, nên hoãn.

Đặc biệt: train hiện đọc được UTF-8-sig và đã có khảo sát vị trí header. Chúng ta còn thiếu quyết định nào, và có đang đầu tư quá mức vào một rủi ro chưa xuất hiện hay không? Ngược lại, train pass có che giấu rủi ro nào khi gặp cấu trúc mới? Hãy cân bằng hai phía bằng bằng chứng.

## 6. Các câu hỏi kỹ thuật cần trả lời

### A. Encoding và văn bản tiếng Việt

1. Với bằng chứng hiện tại, nên làm ngay điều gì cho encoding, điều gì chỉ cần kiểm tra, điều gì nên hoãn? Điều kiện nào mới đủ để mở hỗ trợ TCVN3/VNI hoặc detector phức tạp?
2. Phân biệt byte decoding, chuyển bảng mã/font legacy nếu có, mojibake, Unicode normalization và chuẩn hóa tên/giá trị nghiệp vụ. Đặt từng việc vào lớp nào; việc nào không nên gộp vào encoding detection?
3. Phân tích riêng CSV bytes, chuỗi trong OOXML và SQLite TEXT: rủi ro và điểm can thiệp có giống nhau không? Không đề xuất áp một CSV codec detector vào mọi định dạng nếu không có căn cứ.
4. Decode strict thành công chứng minh điều gì và không chứng minh điều gì? Xử lý thế nào khi chỉ có ASCII, file quá ngắn, nhiều candidate cùng hợp lệ, chuỗi đã bị chuyển mã sai từ trước hoặc có ký tự mất không thể phục hồi chắc chắn?
5. Có cần tách quyết định “codec đọc file” với “giá trị văn bản có vẻ hỏng” không? Làm sao tránh converter sửa hỏng tiếng Việt vốn đúng, ID, tên riêng, mã hàng hoặc ký hiệu?
6. Nếu đề xuất thư viện, giải thích đúng vai trò, giới hạn và cách kiểm đầu ra; không coi confidence thư viện là xác suất đúng đã được calibration cho dữ liệu Việt của project.
7. Đề xuất policy giữ raw/provenance và các trạng thái như known/configured/ambiguous/unsupported nếu cần. Tình huống nào tự xử lý, giữ unresolved, báo lỗi hoặc cần review? Nêu căn cứ, chưa tự đặt ngưỡng thành contract.

### B. Header và vùng bảng

1. Định nghĩa output cần đạt: một row index, một tập header rows, label theo cột, table region, data-start boundary hay row-role classification? Cái nào tối thiểu cần cho A-T2, cái nào vượt sang A-T3/T4?
2. Khảo sát hiện có về header có thể dùng làm annotation/ground truth đến mức nào? Cần kiểm lại điều gì, xử lý nhãn mơ hồ ra sao? Phân biệt annotation dùng chấm detector với annotation được cấp cho chính detector/runtime để tránh đánh giá vòng tròn.
3. Có thể giải quyết trước bằng metadata đã biết và rule-based baseline đơn giản không? So sánh với phương án phức tạp chỉ khi xác định được lỗi mà baseline không giải quyết.
4. Xét các phản ví dụ: title/lời dẫn toàn chữ; header ở hàng sau; nhiều tầng; tên cột trống/trùng; dữ liệu toàn text; header có số/năm; ô sparse/blank; header lặp giữa bảng; và các trường hợp chưa quan sát như merged cells/nhiều vùng bảng. Ghi rõ đâu là observed, synthetic stress case hay giả thuyết.
5. Preview 6 hàng/32 cột và samples hiện tại có đủ để suy luận không? Khi nào cần mở rộng evidence/adaptive reading từ raw cache? Tách giới hạn đầu vào/profile engineering khỏi chiến lược phát hiện cần đánh giá.
6. Bảo toàn mapping từ label/header evidence → vị trí `c0001`… → file/sheet/row/cell thế nào? Có cần đổi raw view hay chỉ thêm lớp metadata/derived schema? Chỉ đề xuất migration khi có lý do rõ.
7. Khi nào được chọn header tự động, khi nào giữ unresolved? Đánh giá trade-off giữa chọn nhầm có vẻ chắc chắn và từ chối chọn. Không dùng một confidence score chưa kiểm chứng làm bảo đảm đúng.
8. Làm sao để header detection không âm thầm biến thành bỏ header/tổng/trùng, fill nhóm, parse số/ngày hoặc cleaning ngoài phạm vi?

### C. Giao diện downstream và giới hạn kết luận

1. Mức thông tin nào đã đủ cho consumer baseline dùng schema raw; thiếu gì để đưa vào prompt thật? Tách lỗi header detection khỏi chất lượng serialization/prompt để có thể đánh giá riêng.
2. Có thể kiểm structural correctness, mapping, preservation và descriptor usefulness ở mức nào khi chưa có model/scorer? Cái gì chỉ được đánh giá sau khi D/E có baseline và split hợp lệ?
3. Làm sao giữ source strings là dữ liệu không tin cậy, không biến title/header/README thành chỉ dẫn thực thi hoặc SQL identifier không kiểm soát?

## 7. Nếu cần research, hãy thiết kế công việc cụ thể

Đừng dừng ở “cần nghiên cứu encoding/header detection”. Với mỗi quyết định ưu tiên, cung cấp:

- Câu hỏi chưa biết và ảnh hưởng nếu quyết định sai.
- Bằng chứng hiện có; khoảng trống thật sự còn lại.
- Giả thuyết có thể bác bỏ, ít nhất một baseline đơn giản và một phương án so sánh; cho phép kết luận không cần thêm tính năng.
- Dữ liệu/annotation tối thiểu cần có, đơn vị đánh giá và quy tắc gán nhãn ambiguous/unknown.
- Thí nghiệm/control/counterexample, phạm vi CPU và chi phí dự kiến; ghi rõ ước lượng chưa đo.
- Metric và cách đọc kết quả: encoding có thể cần độ đúng văn bản/chuyển mã và tỷ lệ làm hỏng văn bản sạch; header có thể cần exact row-set/mapping accuracy, coverage/risk và lỗi tự chọn sai. Hãy chọn metric phù hợp, không buộc dùng tất cả.
- Tiêu chí go/no-go, tiêu chí dừng và fallback. Nếu đưa ngưỡng số, ghi là đề xuất cần xác lập bằng dữ liệu, không giả thành yêu cầu BTC.
- Artifact bàn giao: decision note, annotation spec, fixtures, benchmark/report, policy/config và interface; chỉ chọn những artifact thực sự cần.
- Kết quả nào đủ để chuyển cho engineering triển khai; kết quả nào vẫn chưa chứng minh tổng quát hóa hoặc lợi ích PA.

Đề xuất thiết kế evaluation trong điều kiện **toàn train input đã được khảo sát, E-SPLIT chưa khóa**:

- Không tuning bằng public/private test hoặc gold; không gọi phần train đã quan sát là unseen holdout hoàn toàn.
- Xem xét grouping theo business/source family/template và file trùng/near-duplicate; giải thích giới hạn của split đề xuất.
- Tách dữ liệu chọn quy tắc/ngưỡng khỏi dữ liệu kiểm tra theo access policy được xác lập trước thí nghiệm lựa chọn.
- Phân biệt dữ liệu thật có nhãn với synthetic/perturbation; không dùng synthetic success thay cho bằng chứng phân phối thật.
- Không cần gold câu hỏi để đánh giá encoding/header; nhãn cấu trúc/văn bản cần được xây độc lập và có provenance.
- Nêu thông tin bổ sung tối thiểu cần chủ project trích xuất local nếu thật sự cần. Không yêu cầu upload toàn kit hoặc giả định quyền đưa raw vào dịch vụ bên ngoài.

Nếu literature có ích, chỉ chọn ít nguồn sát quyết định, ưu tiên paper/docs chính thức. Timeline nhắc TableSense và SpreadsheetLLM chỉ là gợi ý đọc, không chứng minh phù hợp hay phải triển khai chúng. Nếu dùng nguồn, kiểm đúng tên, bài toán, dữ liệu, yêu cầu tài nguyên và giới hạn chuyển sang project; dẫn link đã kiểm tra. Nếu không có web/tool, đánh dấu chưa xác minh thay vì bịa trích dẫn. Không cần mở literature review lớn chỉ để chứng minh rằng research là cần thiết.

## 8. Ràng buộc của project

- Raw/input read-only; lớp diễn giải/annotation/cleaning nếu sau này có phải giữ lineage và không sửa raw để làm kết quả đẹp.
- Không hard-code đáp án theo question/business ID. Phân biệt metadata nguồn có fingerprint với luật đặc cách theo ID để khớp train.
- Không đọc gold vào inference, không public/private tuning, không tự coi split/access policy đã tồn tại.
- Local chỉ CPU nhẹ; mọi real model/embedding/reranker/training chạy Modal. Budget tối đa 30 USD/thí nghiệm, cần xác minh account/budget trước job; budget khai báo không phải hard billing cap. Trong yêu cầu tư vấn này không chạy job.
- Chưa có model/scorer/PA baseline; không tạo dependency giả rằng phải có chúng mới làm được kiểm tra cấu trúc ban đầu.
- Dependency qua pyproject.toml/uv.lock; không tự cài thư viện. Docker hoãn tới nhóm G packaging cuối pipeline.
- State/backlog là tracker duy nhất, timeline A–G là kế hoạch hiện hành. Không tạo roadmap cạnh tranh hoặc mở A-T3/T4/B/C/D/E/F/G ngoài phạm vi phân tích liên quan.

## 9. Định dạng câu trả lời tôi cần

Trả lời bằng tiếng Việt, chi tiết nhưng ưu tiên quyết định và bằng chứng hơn độ dài. Cấu trúc mong muốn:

1. **Kết luận trực tiếp:** có cần research không, cần đến mức nào và cho từng phần nào; chỉ rõ việc nào chưa đáng làm lúc này.
2. **Bạn thực sự đã đọc gì:** branch/ref nếu biết, file/section/function; thiếu gì và giới hạn xác minh. Không kể như đã chạy các artifact local.
3. **Phản biện quan điểm hiện tại:** điểm đúng, điểm quá rộng, assumption thiếu bằng chứng và các phản ví dụ quan trọng.
4. **Bảng phân loại công việc:** engineering / validation / empirical research / literature-model research / defer, kèm căn cứ và ưu tiên.
5. **Research agenda tối thiểu trong A-T2:** ma trận câu hỏi → giả thuyết → baseline/phương án → dữ liệu → phép thử → metric → go/no-go → artifact. Encoding và header trình bày riêng.
6. **Policy/interface đề xuất:** raw/decoded/annotation/derived metadata, ambiguity/fallback và cách tận dụng implementation hiện có. Có thể mô tả/pseudocode ngắn nếu giúp quyết định; chưa viết production code.
7. **Evaluation và thứ tự thực hiện:** phần làm được ngay bằng CPU, phần chờ thêm evidence/nhãn, phần chỉ làm sau baseline; phân biệt acceptance detector với acceptance prompt/PA.
8. **Bước nhỏ nhất tiếp theo:** đề xuất một increment cụ thể, acceptance rõ, chưa tự thực hiện. Nếu cần thêm dữ liệu, chỉ nêu vài yêu cầu quan trọng nhất và tiếp tục kết luận có điều kiện từ bằng chứng hiện có.

Tôi muốn sau câu trả lời của bạn có thể biết chính xác: **cần nghiên cứu cái gì, vì sao, kiểm chứng bằng cách nào, khi nào đủ để dừng và giao lại cho engineering**. Kết luận “chưa cần research phức tạp ở một phần” hoàn toàn được chấp nhận nếu bạn chứng minh được từ tình trạng project.
