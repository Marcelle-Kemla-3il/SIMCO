from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
import os

def setup_static_files(app: FastAPI):
    """Setup static files serving"""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
