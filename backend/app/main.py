from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes import router as v1_router

app = FastAPI(title="VEKTRA API")

origins = [
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5502",
    "http://localhost:5502",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "VEKTRA backend running"}
