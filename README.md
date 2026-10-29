# Coffee Invoice Forecast

Starter monorepo for predicting the number of coffee-shop invoices by date and work shift.
Includes a React frontend, FastAPI backend, basic ML baseline, CSV dataset, tests, and docs.
**Docker is intentionally not included yet.**

## Features
- Load and profile the supplied transaction CSV.
- Derive `shift` from `timestamp`: `Night` (00:00–05:59), `Morning` (06:00–11:59),
  `Afternoon` (12:00–16:59), `Evening` (17:00–23:59).
- Derive `is_holiday` as a boolean: `true` when `holiday_name` is populated, otherwise `false`.
- Aggregate transactions into daily invoice counts by shift.
- Run an EDA summary over the transaction dataset and export a markdown report.
- Train a Random Forest baseline and expose prediction/analytics APIs.
- React dashboard with summary cards, prediction form, and historical chart/table.

## Project structure
- `backend/`: FastAPI routes, services, ML baseline, tests.
- `frontend/`: React + Vite + TypeScript.
- `data/raw/`: original dataset.
- `data/processed/`: generated enriched dataset (created on first API run).
- `notebooks/`: reserved for experiments.
- `models/`: saved model artifacts (generated during training).
- `docs/`: data dictionary and project notes.
- `results/`, `logs/`, `config/`: project output/config folders.

## Requirements
- Python 3.11+
- Node.js 20+
- npm

## Run backend (Windows PowerShell)
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs: http://127.0.0.1:8000/docs

## Generate EDA report
Open the notebook at `notebooks/exploratory/eda.ipynb` and run all cells.
It writes the dataset overview to `notebooks/exploratory/EDA_REPORT.md` and includes shift/day-of-week/holiday patterns from the real CSV data.

## Run frontend (new terminal)
```powershell
cd frontend
npm install
npm run dev
```
Frontend: http://localhost:5173

## Notes about target definition
The provided CSV contains transaction-level records and a `transaction_id`, but no explicit invoice-line relationship field. This starter treats each row/`transaction_id` as one invoice/transaction. If one invoice can contain multiple rows, the target should instead count distinct invoice IDs after confirming the dataset's semantics.

The baseline model aggregates the count by `date + shift`, with `is_holiday` calculated from `holiday_name`. It is a starter model, not a production forecasting system. Evaluation should use a chronological holdout and compare against a simple baseline.

## Team workflow
See `docs/TEAM_ASSIGNMENT.md`. Each member owns separate folders/modules and can work concurrently against the documented API contract.

# Task thành viên 2 — Phạm Tấn Khánh (ML & Evaluation)

Các file chỉ nằm trong phạm vi thành viên 2 được phân công. **Chép đè các file này vào đúng đường dẫn trong repo `CoffeeInvoicePrediction`** (đừng xóa file của các thành viên khác).

### Cách chạy trên Windows PowerShell (tại gốc repo)
```powershell
cd backend
pip install -r requirements.txt
cd ..
python results/run_evaluation.py
```

Đầu ra:
- `results/evaluation_metrics.json`: MAE, RMSE và khoảng ngày train/test.
- `models/invoice_count_rf.joblib`: mô hình huấn luyện toàn bộ lịch sử.
- `results/ML_REPORT.md`: giải thích pipeline và hạn chế.
- `notebooks/ML_Experiment.ipynb`: notebook thử nghiệm.

Dữ liệu nguồn của dự án phải nằm tại `data/raw/coffee_shop_sales.csv`. Nếu chạy thiếu dữ liệu sẽ báo lỗi rõ ràng. **Không tự điền số MAE/RMSE không có dữ liệu thật**.

### Git branch
```powershell
git switch -c feature/member-2-ml
git add backend/app/ml/model_service.py notebooks/ML_Experiment.ipynb models/.gitkeep results/run_evaluation.py results/ML_REPORT.md results/.gitkeep
git commit -m "feat(ml): chronological evaluation and invoice prediction"
git push -u origin feature/member-2-ml
```

`results/evaluation_metrics.json` và `models/invoice_count_rf.joblib` là output sinh từ dữ liệu thực; hãy kiểm tra `.gitignore` của dự án trước khi quyết định commit các file đó.
