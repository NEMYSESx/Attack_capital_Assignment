from fastapi import APIRouter
from app.api.endpoints import rooms, agents, tokens

api_router = APIRouter()

api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["tokens"])