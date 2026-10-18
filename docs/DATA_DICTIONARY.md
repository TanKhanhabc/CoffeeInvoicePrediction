# Data dictionary and feature rules

## Source data
`data/raw/coffee_shop_sales.csv` is the original supplied dataset. It contains transaction-level records.

## Derived columns
- `date`: calendar date extracted from `timestamp` (`YYYY-MM-DD`).
- `hour`: hour extracted from `timestamp` (0–23).
- `shift`: `Night` for 00:00–05:59; `Morning` for 06:00–11:59;
  `Afternoon` for 12:00–16:59; `Evening` for 17:00–23:59.
- `is_holiday`: boolean `true` if `holiday_name` is not null/blank; otherwise `false`.
- `day_of_week`: Monday=0 through Sunday=6.
- `month`: month number 1–12.

## Prediction target
`invoice_count`: number of transaction rows per `date + shift`. The supplied data has `transaction_id`;
this starter assumes one row corresponds to one invoice/transaction. Confirm this assumption before reporting
business results.

## Source columns observed
`transaction_id`, `timestamp`, `store_id`, `city`, `country`, `store_type`, `product_category`,
`product_name`, `unit_price`, `quantity`, `discount_applied`, `payment_method`, `customer_id`,
`customer_age_group`, `customer_gender`, `loyalty_member`, `weather_condition`, `temperature_c`,
`holiday_name`, `total_amount`.
