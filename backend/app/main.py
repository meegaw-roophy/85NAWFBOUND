from fastapi import FastAPI
from app.api.v1.routes import router as v1_router

app = FastAPI(title="VEKTRA API")

app.include_router(v1_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "VEKTRA backend running"}
