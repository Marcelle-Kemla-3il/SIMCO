from fastapi import APIRouter
from app.api.v1.endpoints import quiz, cognitive, admin

api_router = APIRouter()

api_router.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
api_router.include_router(cognitive.router, prefix="/cognitive", tags=["cognitive"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
