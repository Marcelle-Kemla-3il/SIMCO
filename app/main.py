from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.v1.api import api_router
import os

app = FastAPI(
    title="SIMCO - Système Intelligent Multimodal d'Évaluation Cognitive",
    description="Système d'évaluation cognitive utilisant LLM, vision par ordinateur et ML",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "SIMCO API - Système d'Évaluation Cognitive"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SIMCO Backend"}

@app.get("/demo")
async def demo():
    """Page de démonstration du quiz"""
    from fastapi.responses import FileResponse
    demo_file = os.path.join(static_dir, "quiz_demo.html")
    if os.path.exists(demo_file):
        return FileResponse(demo_file)
    return {"error": "Demo page not found"}
