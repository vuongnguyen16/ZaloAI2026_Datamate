# Chốt quyền dev và tiêu chí G2 G5 ngày 06/11/2026

Đã ghi quyết định người dùng trước triển khai P2: quyền dev trên Modal,
lưới an toàn/probe đi trước nghiệp vụ, G2 thu gọn và G5 là quy tắc quyết định
kỹ thuật. Xác nhận ngưỡng mới nhất thay lựa chọn giữ dự thảo trước đó.
P2/P5 vẫn todo; chưa có code P2, job model, upload dev hoặc PA mới; G2/G5 chưa pass.

Nguồn: DOCX hiện hành (bản cập nhật06/11),
[quyết định](../docs/research/p2_g2_g5_decisions.md),
[policy G5](../configs/g5_decision_policy.json). State/backlog là tracker duy nhất.

G5 mới: so với cấu hình đang được chấp nhận, cùng toàn dev ID/model/revision/
tokenizer/seed/scorer. Kỹ thuật deltaPA>=+0.01; đơn giản hóa có bằng chứng
deltaPA>=-0.005. Cả hai nhánh: >=3/4cụm có điểm ròng>=-1, mọi cụm có điểm
ròng>=-max(0.01*N_c,2); runtime trong budget đoP3. Hai CI bootstrap chỉ mô tả;
không dùng calibration chấm từng kỹ thuậtP5, P6 kiểm cấu hình cuối/ngưỡng,
P7 holdout một lần. Bootstrap/scorer/split/access P0 không đổi.

Kiểm biên bằng Fraction chính xác: global18fail/19pass, simplification-9pass/
-10fail, hai cụm vượt dung sai-1 bị loại, cụm100câu mất3điểm bị loại;
ngưỡng mất điểm nguyên vớiN_c=50/100/199/200/250/1000 lần lượt2/2/2/2/2/10.
Đây là kiểm contract giấy tờ, không là implementation hoặc acceptance G5 runtime.

Review độc lập read-only theo requesting-code-review:1Important,0Critical;
phát hiện B4/P4 còn chọn ngưỡng calibration trướcP6. Đã sửa DOCX và backlog:
P4 ngưỡng tạm dev, calibrationP6, rồi xuất/hash lại. Reviewer không đọc
data/gold/kit/runs; không đánh giá QA hình ảnh, live quyền/budget hay runtime.
Các phần đó do tác giả kiểm hoặc để đúng pha, không suy từ review source.

DOCX giữ20bảng/149hàng và1sơ đồ, sửa sơ đồ P2 và nhãn các việc chuyển pha;
bản web/asset/manifest/backlog cùng hash nguồn. UTF-8/NFC/JSON và protected
split/access/scorer/model manifest/root pyproject+lock được kiểm không đổi.

Môi trường documents managed Node không khởi động được; sửa bằng môi trường
CPU riêng tại scratch, dependencies qua pyproject+uv.lock, không đổi runtime
DataMate hoặc cài GPU local. LibreOffice26.2.6 MSI chính thức được kiểm SHA256
`f9877032fd908beb9c0ddf06df4af5c2e85f419c42e14876c4cce5aae5fb2660`,
chỉ giải nén administrative image tại scratch, không cài ứng dụng hệ thống.
PDF thật do LibreOffice headless; render_docx.py dùng adapter PyMuPDF thay
Poppler để raster. Hai lần thử trước khi giải nén xong thất bại do runtime
chưa đầy đủ; lần cuối sau extraction exit0 đã render đủ16trang. Tác giả đã
mở kiểm toàn bộ16ảnh trang, gồm tiêu đề, sơ đồ, bảng và công thức; không
clipping/overlap/mất dấu tiếng Việt. Source/hash không đổi sau render.

CPU mới: `uv run --locked python scripts/check.py` exit0,
**314 passed, 1 skipped in43.55s**, Ruff lint/format pass, source không đổi
trong gate. Đã đọc gate.json và ba log tại
`runs/cpu-check-20261106T113002356608Z-kn2e1qpb/gate.json`.
Skip duy nhất là fixture symlink thiếu quyền trên Windows, test không bị bỏ.
Timeline check current, nguồn DOCX
`499fe26b696d5d8eb5d71117c927e57438cbfa96064934da5e2fccc918451d28`;
137đoạn có chữ/20bảng/149hàng/1sơ đồ. Context P2 passed/current, dependency
ready, không active task/warning/planning error; kiểm lại sau commit.

Các phần reviewer không kết luận: QA hình ảnh và CPU đã được tác giả kiểm
như trên; runtime G2/G5, dữ liệu/artifact thật và live quyền/budget để đúng
pha, không lấy giấy tờ thay bằng chứng. Không có job cloud trong phiên này.

Người dùng sau đó yêu cầu đưa lên GitHub. Đã fast-forward `main` và push
[800e4d6](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/commit/800e4d65b225df2431ac23d84d9a6d66eae74798),
SHA remote khớp. [CI của commit policy](https://github.com/vuongnguyen16/ZaloAI2026_Datamate/actions/runs/42211822444)
success, **315 passed in15.16s** trên Ubuntu, Ruff pass; đã đọc steps/log.
Đây là bằng chứng cho800e4d6; commit bổ sung bản ghi này kiểm CI riêng.
Chỉ code/config/tài liệu phù hợp được xuất bản, không dữ liệu BTC/gold/runs
hoặc scratch QA. Không có job model mới hoặc thay trạng thái P2/P5.
