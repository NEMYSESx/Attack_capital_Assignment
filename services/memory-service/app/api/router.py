from fastapi import APIRouter
from app.api.endpoints.memory import router as memory_router 

api_router = APIRouter()

api_router.include_router(memory_router)
