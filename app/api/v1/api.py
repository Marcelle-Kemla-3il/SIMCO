from fastapi import APIRouter
from app.api.v1.endpoints import quiz, agent, agent_fast, cv, admin

api_router = APIRouter()

api_router.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(agent_fast.router, prefix="/agent-fast", tags=["agent-fast"])
api_router.include_router(cv.router, prefix="/cv", tags=["cv"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
