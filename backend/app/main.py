import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints

app = FastAPI(title="Candidate Intelligence Engine API", version="1.0")

# Load allowed origins from environment variable or use a safe default
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}
