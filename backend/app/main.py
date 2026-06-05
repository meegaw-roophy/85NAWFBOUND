from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes import router as v1_router
from app.core.config import settings

app = FastAPI(title="VEKTRA API", docs_url=None, redoc_url=None)

origins = [o.strip() for o in settings.ALLOWED_CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "VEKTRA backend running"}
