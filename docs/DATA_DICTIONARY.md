# Data Dictionary & Data Profile

Người phụ trách: Lê Trung Hưng (Thành viên 1 — Xử lý dữ liệu).
Mã nguồn liên quan: `backend/app/services/data_service.py`, `backend/tests/test_data_service.py`.

## 1. Nguồn dữ liệu

| Mục | Giá trị |
|---|---|
| File | `data/raw/coffee_shop_sales.csv` |
| Số dòng / số cột | 20.000 / 20 |
| Khoảng thời gian | 2023-01-01 00:39:39 → 2023-12-31 22:54:02 (365 ngày liên tục, đủ cả năm) |
| Số cửa hàng | 45 (`store_id`) |
| Quốc gia | USA 6.685 · CAN 4.571 · AUS 4.392 · UK 4.352 dòng |
| Múi giờ | `timestamp` không có múi giờ; coi là giờ địa phương của từng cửa hàng |

Mỗi dòng là một giao dịch. `transaction_id` chạy từ 10001 đến 30000, không trùng, không rỗng, và file đã được sắp theo thời gian.

## 2. Các cột gốc

Mô tả ý nghĩa được suy ra từ dữ liệu mẫu, không phải từ tài liệu của nguồn dữ liệu.

| Cột | Kiểu (pandas) | Thiếu | Ghi chú |
|---|---|---:|---|
| `transaction_id` | int64 | 0 | Mã giao dịch / hóa đơn, duy nhất |
| `timestamp` | object → datetime | 0 | Dạng `YYYY-MM-DD HH:MM:SS` (19 ký tự, 20.000/20.000 dòng hợp lệ) |
| `store_id` | int64 | 0 | Mã cửa hàng |
| `city`, `country` | object | 0 | Thành phố, mã quốc gia (USA/CAN/AUS/UK) |
| `store_type` | object | 0 | Ví dụ Mall Kiosk, Standalone, Airport |
| `product_category`, `product_name` | object | 0 | Nhóm và tên sản phẩm |
| `unit_price` | float64 | 0 | Đơn giá, luôn > 0 |
| `quantity` | int64 | 0 | Số lượng, luôn > 0 |
| `discount_applied` | bool | 0 | Có giảm giá hay không |
| `payment_method` | object | 0 | Credit Card, Debit Card, Mobile Wallet, Cash… |
| `customer_id` | object | 0 | Mã khách hàng ẩn danh |
| `customer_age_group` | object | 1.076 | Nhóm tuổi; thiếu = không có thông tin |
| `customer_gender` | object | 1.072 | Giới tính; thiếu = không có thông tin |
| `loyalty_member` | bool | 0 | Thành viên thân thiết |
| `weather_condition` | object | 978 | Thời tiết |
| `temperature_c` | float64 | 978 | Nhiệt độ (°C) |
| `holiday_name` | object | 19.665 | **Rỗng = không phải ngày lễ**; không phải dữ liệu lỗi |
| `total_amount` | float64 | 0 | Thành tiền (có vẻ bằng `unit_price × quantity`, trừ giảm giá nếu có) |

## 3. Cột được tạo thêm

| Cột | Kiểu | Quy tắc |
|---|---|---|
| `date` | str `YYYY-MM-DD` | Ngày của `timestamp` |
| `hour` | int | Giờ (0–23) |
| `shift` | str | Night 00:00–05:59 · Morning 06:00–11:59 · Afternoon 12:00–16:59 · Evening 17:00–23:59 |
| `is_holiday` | bool | `True` khi `holiday_name` có nội dung (sau khi bỏ khoảng trắng), ngược lại `False`. Mức **dòng** |
| `is_holiday_date` | bool | `True` cho mọi dòng của ngày có ít nhất một dòng lễ. Mức **ngày** |
| `day_of_week` | int | 0 = Thứ Hai … 6 = Chủ Nhật |
| `month` | int | 1–12 |

Ví dụ: `08:30` → Morning, `16:59:59` → Afternoon, `17:00:00` → Evening, `holiday_name = null` → `is_holiday = False`.

## 4. Bảng tổng hợp (target)

`aggregate_invoice_counts(df)` trả về một dòng cho mỗi `date + shift`:

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `date` | str `YYYY-MM-DD` | Ngày |
| `shift` | str | Night / Morning / Afternoon / Evening |
| `is_holiday` | bool | `True` nếu **bất kỳ** dòng nào của ngày đó là ngày lễ |
| `invoice_count` | int | Số `transaction_id` duy nhất. **Target của mô hình** |
| `day_of_week`, `month` | int | Suy ra từ `date` |

Quy ước:
- Mỗi ngày luôn có đủ 4 ca; ca không có giao dịch được ghi `invoice_count = 0`.
- Sắp xếp theo ngày, rồi theo thứ tự ca Night → Morning → Afternoon → Evening (không sắp theo bảng chữ cái).
- Với dữ liệu hiện tại: 365 ngày × 4 ca = **1.460 dòng**, tổng `invoice_count` = 20.000.
- `holiday_mode="row"` cho phép gom đúng nghĩa đen theo `is_holiday` mức dòng (xem mục 5.2). Chế độ này không điền ca trống.

## 5. Kết quả kiểm tra dữ liệu

### 5.1 Chất lượng

| Kiểm tra | Kết quả |
|---|---|
| Dòng trùng hoàn toàn | 0 |
| `transaction_id` trùng | 0 |
| `transaction_id` rỗng | 0 |
| `timestamp` không parse được | 0 |
| `quantity` hoặc `unit_price` ≤ 0 | 0 |
| Thiếu ở cột phân tích khác | `customer_age_group` 1.076; `customer_gender` 1.072; `weather_condition`, `temperature_c` 978. Không ảnh hưởng target |

Vì không có `transaction_id` trùng, giả định "1 dòng = 1 hóa đơn" của nhóm phù hợp với dữ liệu này.

### 5.2 Ngày lễ

| Ngày lễ | Số dòng |
|---|---:|
| Christmas Day | 103 |
| New Year's Day | 97 |
| Independence Day | 39 |
| Boxing Day | 33 |
| Veterans Day | 31 |
| Canada Day | 18 |
| Australia Day | 14 |
| **Tổng** | **335** (1,7% số dòng) |

**Phát hiện quan trọng:** trong 7 ngày lễ, có **5 ngày** mà chỉ một số dòng được đánh dấu lễ, còn các dòng khác cùng ngày thì không. Số liệu lấy từ `data/processed/data_profile.json`:

| Ngày | Ngày lễ | Loại |
|---|---|---|
| 2023-01-01 | New Year's Day | Cả ngày (mọi dòng đều được đánh dấu) |
| 2023-12-25 | Christmas Day | Cả ngày (mọi dòng đều được đánh dấu) |
| 2023-01-26 | Australia Day | **Lẫn** |
| 2023-07-01 | Canada Day | **Lẫn** |
| 2023-07-04 | Independence Day | **Lẫn** |
| 2023-11-11 | Veterans Day | **Lẫn** |
| 2023-12-26 | Boxing Day | **Lẫn** |

Suy ra từ tên ngày lễ: `holiday_name` phụ thuộc quốc gia (Australia Day của Úc, Canada Day của Canada, Independence Day và Veterans Day của Mỹ, Boxing Day không áp dụng ở Mỹ). Các dòng cùng ngày ở quốc gia khác có `holiday_name` rỗng.

Nếu gom theo `is_holiday` mức dòng, mỗi ngày như vậy bị tách thành hai nhóm cho cùng một `date + shift`, và cả hai đều chỉ là số đếm một phần. Vì vậy `aggregate_invoice_counts` mặc định dùng cờ mức **ngày** (`holiday_mode="date"`): một dòng cho mỗi `date + shift`, `invoice_count` là tổng của mọi cửa hàng.

Hệ quả cần nhóm biết: với 5 ngày này, `is_holiday = True` nghĩa là "có ít nhất một quốc gia nghỉ lễ", không phải "mọi cửa hàng nghỉ lễ".

### 5.3 Phân bố theo ca (số dòng giao dịch)

| Ca | Số dòng | Tỷ lệ |
|---|---:|---:|
| Morning | 9.806 | 49,0% |
| Afternoon | 5.982 | 29,9% |
| Evening | 2.702 | 13,5% |
| Night | 1.510 | 7,6% |

### 5.4 Thống kê bảng tổng hợp (1.460 nhóm date + shift)

| Chỉ tiêu | Giá trị |
|---|---:|
| Số nhóm | 1.460 (365 ngày × 4 ca) |
| Tổng `invoice_count` | 20.000 (khớp số dòng gốc) |
| Nhóm có `invoice_count = 0` | 14 |
| Nhỏ nhất / lớn nhất / trung bình | 0 / 56 / 13,70 |

Trung bình số hóa đơn mỗi ca:

| Ca | Trung bình |
|---|---:|
| Morning | 26,87 |
| Afternoon | 16,39 |
| Evening | 7,40 |
| Night | 4,14 |

Ca Night rất thưa (trung bình khoảng 4 hóa đơn mỗi ngày), nên số đếm theo ngày của ca này dao động mạnh. Có 14 nhóm bằng 0, đây là những ca không có giao dịch nào và đã được điền bằng 0 thay vì bị mất dòng.

## 6. Giả định và hạn chế

1. Một dòng = một hóa đơn (đã kiểm tra: không trùng `transaction_id`).
2. Dữ liệu gộp mọi cửa hàng và mọi quốc gia; không có thông tin theo từng cửa hàng ở bảng tổng hợp.
3. `timestamp` được coi là giờ địa phương; chưa quy đổi múi giờ.
4. Dữ liệu chỉ có một năm (2023), nên mô hình chưa thấy được yếu tố mùa vụ qua nhiều năm.
5. Ngày lễ chỉ có 7 loại và 335 dòng, nên số mẫu "lễ" rất ít.
6. Dòng có `timestamp` lỗi sẽ bị loại và được đếm trong `invalid_timestamp_rows` (hiện bằng 0).

## 7. Tạo lại dữ liệu đã xử lý

Chạy từ thư mục `backend/` (môi trường ảo đã bật):

```powershell
python -m app.services.data_service
```

Lệnh này ghi vào `data/processed/`:
- `coffee_shop_sales_enriched.csv`: dữ liệu giao dịch cùng các cột mới
- `invoice_counts_by_date_shift.csv`: bảng tổng hợp theo mục 4
- `data_profile.json`: báo cáo kiểm tra dữ liệu

Chạy kiểm thử:

```powershell
python -m pytest tests/test_data_service.py -v
```
