# Kết quả tinh chỉnh mô hình

Chạy từ thư mục gốc: `python results/run_evaluation.py`.

Giữ nguyên API `predict_count(date, shift, is_holiday) -> int` và bốn đặc trưng hiện tại.

20% ngày cuối (2023-10-20 đến 2023-12-31) được giữ riêng để kiểm thử. Trên 80% ngày đầu, chọn theo MAE trung bình của ba cửa sổ kiểm định mở rộng theo thời gian. Các ca cùng ngày luôn nằm cùng tập. So sánh baseline trung bình theo ca với sáu cấu hình Random Forest: min_samples_leaf 2/8/20, max_depth 6/None, 200 cây, seed 42. Baseline cũng có thể được chọn nếu tốt hơn.

| Mô hình | MAE | RMSE |
| --- | ---: | ---: |
| Trung bình theo ca | 3.7937 | 5.2618 |
| Random Forest cấu hình cũ | 3.4203 | 4.9149 |
| Chọn bằng kiểm định thời gian | 3.1858 | 4.5935 |

Cấu hình được chọn khi đánh giá: min_samples_leaf=2, max_depth=6. MAE giảm khoảng 6.9%, RMSE giảm khoảng 6.5% trên cùng tập kiểm thử. Đây là sai số dự đoán số thực trước làm tròn; API trả số nguyên không âm. Chi tiết nằm trong `evaluation_metrics.json`.

Sau đánh giá, model triển khai được chọn lại bằng kiểm định trên toàn bộ lịch sử rồi fit toàn bộ dữ liệu; cấu hình có thể khác cấu hình đánh giá holdout. File joblib lưu cấu hình, điểm CV, schema và số dòng. Cache được làm mới theo thời gian sửa file; khi chưa có file model, cache mô hình theo thời gian sửa dữ liệu nguồn.

Kết quả cũ trong repository dùng số dòng tổng hợp khác nên không dùng trực tiếp để tính mức cải thiện. Các chỉ số trên dùng data service hiện tại với đầy đủ lưới ngày–ca và cờ ngày lễ theo ngày.

Giới hạn: chỉ một năm dữ liệu và một tập kiểm thử cuối kỳ, chưa bảo đảm mức cải thiện cho các năm tiếp theo. Cờ ngày lễ phải biết trước khi dự đoán. Chưa sử dụng đặc trưng trễ vì API cho phép dự đoán ngày bất kỳ mà không cung cấp lịch sử gần ngày đó.

Kiểm thử backend: từ `backend/`, chạy `python -m pytest tests -q`. Kiểm thử riêng ML: `python -m pytest tests/test_model_service.py -v`.
