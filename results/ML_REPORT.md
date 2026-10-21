# Báo cáo Machine Learning — Phạm Tấn Khánh

## 1. Mục tiêu và dữ liệu
Dự đoán số lượng hóa đơn (`invoice_count`) theo `date`, `shift`, `is_holiday`. Từ CSV giao dịch, data service của nhóm đếm số `transaction_id` khác nhau theo đúng 3 trường này. Quy ước ca: Night 00–05, Morning 06–11, Afternoon 12–16, Evening 17–23. Ngày lễ được xác định theo việc `holiday_name` có nội dung.

## 2. Tiền xử lý, đặc trưng
Đầu vào ML là bảng đã tổng hợp, mỗi dòng ứng với một bộ (`date`, `shift`, `is_holiday`). Dùng các biến `day_of_week`, `month`, `shift_code`, `is_holiday`. Không đưa `invoice_count` vào biến đầu vào, tránh rò rỉ nhãn.

## 3. Mô hình thử nghiệm
- Baseline: dự đoán trung bình số hóa đơn của từng ca trong dữ liệu huấn luyện; ca chưa xuất hiện dùng trung bình toàn bộ.
- Random Forest Regressor: 200 cây, `min_samples_leaf=2`, `random_state=42`.

## 4. Phương pháp đánh giá
Tách theo **ngày**: 80% ngày đầu để huấn luyện, 20% ngày cuối để kiểm thử. Tất cả ca của cùng một ngày nằm trong một tập. Đánh giá cả hai mô hình trên cùng tập kiểm thử với MAE và RMSE (càng thấp càng tốt). Tuyệt đối không báo điểm trên dữ liệu huấn luyện như điểm kiểm thử.

**Kết quả thực:** chạy `python results/run_evaluation.py` trong thư mục gốc repo khi đã có file `data/raw/coffee_shop_sales.csv`. Script tạo `results/evaluation_metrics.json` chứa kết quả có thể kiểm chứng. Chưa có kết quả số thực trong tài liệu này vì dữ liệu nguồn chưa được tải xuống môi trường tạo bản giao này.

## 5. Giới hạn và hướng cải thiện
- Một `transaction_id` được xem là một hóa đơn; nếu nhiều dòng ứng với một hóa đơn cần xác minh trước khi công bố kết luận.
- Dataset có thể không có bản ghi cho ca không phát sinh giao dịch, khiến mô hình khó học số 0; cần bổ sung đầy đủ lưới ngày–ca sau khi làm rõ nghiệp vụ.
- `is_holiday` cần biết trước cho ngày dự đoán; không suy từ kết quả bán hàng trong tương lai.
- Một lần tách holdout chưa đủ để khẳng định độ ổn định; nên thử rolling backtesting và xem sai số theo từng ca, ngày lễ.
- Chỉ nên dùng Random Forest thay baseline nếu MAE/RMSE trên tập tương lai thực sự tốt hơn.

## 6. Tích hợp
Hàm `predict_count(target_date: str, shift: str, is_holiday: bool) -> int` giữ nguyên với API hiện tại. Nếu chưa có mô hình lưu, hàm tự huấn luyện từ data service; khi chạy script đánh giá sẽ lưu mô hình vào `models/invoice_count_rf.joblib` để các lần dự đoán sau không cần huấn luyện lại.
