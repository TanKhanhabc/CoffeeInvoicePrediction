from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import data, predictions

app = FastAPI(title="Coffee Invoice Forecast API", version="0.1.0",
              description="Starter API for predicting coffee-shop invoice counts.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(data.router)
app.include_router(predictions.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Coffee Invoice Forecast API"}
