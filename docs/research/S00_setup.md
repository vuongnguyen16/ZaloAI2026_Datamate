# S00 — Quyết định thiết lập ban đầu

Ngày kiểm tra: 01/11/2026. Phạm vi: CPU harness, format stub, cloud CPU smoke; không chọn model hoặc tối ưu PA.

## Bằng chứng và lựa chọn

- **Quan sát local:** repo Git chưa có commit/remote; kit và thể lệ đã có; Python PATH là MSYS2 3.12.11, uv chưa có PATH. RAM khả dụng thấp nên giới hạn fixture/threads thay vì dùng toàn máy.
- **Quyết định người dùng:** mọi model thật trên Modal; profile/workspace `vuonghungnguyen07`; tối đa 30 USD/thí nghiệm.
- **Quan sát từ kit:** question schema và output ví dụ khớp contract ghi trong `docs/requirements.md`. Chưa có evaluator/runner gốc nên stub chỉ kiểm tra format.
- **Nguồn nghiên cứu:** [uv installation](https://docs.astral.sh/uv/getting-started/installation/), [installer options](https://docs.astral.sh/uv/reference/installer/), [projects](https://docs.astral.sh/uv/guides/projects/), [locking/sync](https://docs.astral.sh/uv/concepts/projects/sync/), [pytest usage](https://docs.pytest.org/en/stable/how-to/usage.html), [Modal guide](https://modal.com/docs/guide), [Modal profile CLI](https://modal.com/docs/reference/cli/profile), [token CLI](https://modal.com/docs/reference/cli/token). Đã đọc bằng TinyFish; không làm deep research.

Chọn CPython 3.11.18 managed + uv 0.13.6 ở workspace, `src/datamate`, pytest/Ruff và lock. Có thể dùng Python hệ thống + venv nhưng dễ nhầm MSYS2 interpreter và cần cơ chế lock riêng; lựa chọn hiện tại đã chạy import/test. Nếu kit/engine ở P04 không hỗ trợ Python này, đổi có bằng chứng và tái kiểm tra lock cả local/cloud.

Chọn DuckDB chỉ cho phép tính synthetic với schema rõ, code VARCHAR và amount DECIMAL(18,2). Phương án thay là SQLite/decimal Python; chưa có dữ liệu thực nghiệm để chốt ingestion P03. Smoke không kiểm chứng mọi format Excel/SQLite hoặc rounding. Không tự mặc định rounding tie của BTC.

Fake adapter trả response fixture theo thứ tự để chứng minh wiring; không hard-code theo ID nghiệp vụ và không chạy model. SQL smoke là fixture tin cậy. Sandbox/process timeout cho SQL model là dependency P04, chưa được giải quyết bằng DuckDB connection này.

Cloud CPU dùng SDK group riêng, image copy allowlist source/lock/config/synthetic; không tự mount repo/data. Package cài từ lock vào Linux venv trong image, không copy venv Windows. API function được đối chiếu trực tiếp SDK Modal 1.6.3: `block_network`, `serialized`, resource/concurrency/timeout. Network probe chỉ xác nhận request ngoài thất bại dưới policy chặn egress; chưa thay phép nghiệm thu Docker hoàn chỉnh.

## Phép thử và điều kiện giữ

Giữ thiết lập nếu: lock sync thành công; hai câu synthetic đúng số/mã; invalid config/IDs fail rõ; response lỗi có abstain/log và câu tiếp chạy; input không đổi; cổng fail với assertion cố ý sai. Đo PA chỉ khi có scorer và model thật. Kết quả, lệnh và cổng đang chờ ở `reports/s00_setup.md`.
