from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="SIMCO Logic",
    description="FastAPI backend for SIMCO logic services",
    version="0.1.0",
)

app.include_router(router)
