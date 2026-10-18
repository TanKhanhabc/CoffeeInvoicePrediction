# Phân công song song cho 4 thành viên

## Nguyên tắc
Không phân công theo chuỗi "người 1 xong rồi người 2 mới bắt đầu". Cả 4 thành viên bắt đầu ngay từ ngày đầu, dựa trên interface, dữ liệu và API contract đã thống nhất. Mỗi người có module/file riêng, có thể dùng mock/stub trong khi phần khác chưa hoàn tất.

## Phân công theo module độc lập (25% mỗi người)

### Thành viên 1 — Data profiling & feature engineering
**File sở hữu:** `backend/app/services/data_service.py`, `backend/tests/test_data_service.py`, `docs/DATA_DICTIONARY.md`, `data/processed/`.
**Làm ngay:**
- Kiểm tra dữ liệu nguồn, missing, duplicate, kiểu dữ liệu, khoảng thời gian.
- Viết xử lý `shift` và `is_holiday`.
- Tạo hàm `load_enriched_data()`, `aggregate_invoice_counts()`, `get_data_profile()`.
- Viết test cho mốc ca và holiday true/false.
**Không cần chờ:** dùng trực tiếp CSV gốc. Các hàm/đầu ra được quy định trong data dictionary.

### Thành viên 2 — ML model & evaluation
**File sở hữu:** `backend/app/ml/model_service.py`, `notebooks/`, `models/`, `results/`.
**Làm ngay:**
- Viết phiên bản đầu của pipeline ML với dữ liệu mẫu do tự tạo hoặc DataFrame mock theo schema trong `docs/DATA_DICTIONARY.md`.
- Xác định target `invoice_count` theo `date + shift + is_holiday`.
- Thử baseline đơn giản và Random Forest; đánh giá theo thời gian bằng MAE/RMSE.
- Cung cấp hàm công khai `predict_count(target_date: str, shift: str, is_holiday: bool) -> int`.
**Không cần chờ:** không import data_service trong giai đoạn đầu; dùng fixture/mock schema, sau đó adapter sang hàm xử lý dữ liệu của thành viên 1. Chỉ tích hợp khi interface đã ổn định.

### Thành viên 3 — Backend API contract & routes
**File sở hữu:** `backend/app/main.py`, `backend/app/routers/`, `backend/tests/test_api.py`, `backend/requirements.txt`, `docs/API_CONTRACT.md`.
**Làm ngay:**
- Tạo FastAPI app và route `GET /api/health`, `/api/overview`, `/api/history`, `/api/data-profile`, `POST /api/predict`.
- Tạo service giả/stub trả dữ liệu cố định để API chạy được trước khi ML/data xong.
- Viết schema request/response và test route bằng mock.
- Chốt CORS cho `http://localhost:5173`.
**Không cần chờ:** route gọi interface/stub đã chốt, không cần đợi mô hình thật.

### Thành viên 4 — Frontend dashboard
**File sở hữu:** toàn bộ `frontend/`.
**Làm ngay:**
- Xây dashboard với thẻ thống kê, biểu đồ, bảng lịch sử.
- Tạo form ngày dự đoán, ca làm, checkbox `is_holiday` true/false.
- Tạo `api.ts` theo contract và mock JSON nếu backend chưa chạy.
- Hoàn thiện loading/error/empty states và responsive.
**Không cần chờ:** phát triển UI với mock JSON; khi backend chạy, chỉ đổi sang API thật.

## Interface chốt trước để tránh phụ thuộc
- Shift: `Night | Morning | Afternoon | Evening`.
- Holiday: `is_holiday: boolean`; true khi `holiday_name` có nội dung, false nếu trống/null.
- Target: `invoice_count` nhóm theo `date + shift + is_holiday`.
- Predict request: `{ "date": "YYYY-MM-DD", "shift": "Morning", "is_holiday": false }`.
- Predict response: `{ "date": "...", "shift": "...", "is_holiday": false, "predicted_invoice_count": 12 }`.
- API base URL: `http://127.0.0.1:8000`; frontend dev URL `http://localhost:5173`.

## Nhịp làm việc
- **Ngày 1, cùng bắt đầu:** mỗi người tạo branch riêng và hoàn thành skeleton/mock của module mình.
- **Ngày 2:** tiếp tục làm độc lập, chạy unit test; trao đổi interface nếu phát hiện khác biệt.
- **Ngày 3:** ghép các module theo contract; thay stub/mock bằng service/model thật.
- **Ngày 4:** kiểm thử end-to-end, sửa lỗi và chuẩn bị demo.
- Mỗi người commit riêng và tạo Pull Request. Tránh cùng sửa một file.
- Docker để giai đoạn sau, không đưa vào starter hiện tại.
