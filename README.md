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
