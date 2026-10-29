# API contract

Base URL: `http://localhost:8000`

- `GET /api/health` — health check.
- `GET /api/overview` — dataset row count, date range, unique stores, holiday rows, daily aggregate count.
- `GET /api/history?limit=30` — recent date/shift actual counts.
- `POST /api/predict` — request `{ "date": "2023-11-20", "shift": "Morning", "is_holiday": false }`;
  response includes `predicted_invoice_count` and echoed inputs.
- `GET /api/data-profile` — column count, missing values, duplicate rows, derived-column descriptions.
- `GET /api/eda` — exploratory summary with shift mix, holiday share, top products/cities, and weekday distribution.

Shift values: `Night`, `Morning`, `Afternoon`, `Evening`.
