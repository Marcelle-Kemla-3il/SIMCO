from fastapi import FastAPI
from app_cv.routes import router

app = FastAPI(title="SIMCO CV Service", version="1.0.0")

app.include_router(router, prefix="/cv")


@app.get("/health")
async def health():
    return {"status": "ok"}
