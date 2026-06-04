import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.api.v1.routes import router as v1_router
from app.core.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="VEKTRA API", docs_url=None, redoc_url=None)

origins = [o.strip() for o in settings.ALLOWED_CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error("Database integrity error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=409,
        content={"detail": "A database conflict occurred. The record may already exist."},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal database error occurred."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )


app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "VEKTRA backend running"}
