import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.requests import MemoryStoreRequest, MemoryRetrieveRequest
from app.models.responses import MemoryResponse, MemorySearchResponse, HealthResponse
from app.services.memory_service import MemoryService
from app.services.mem0_client import get_mem0_client, health_check_mem0
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Memory"])

limiter = Limiter(key_func=get_remote_address)

def get_memory_service() -> MemoryService:
    settings = get_settings()
    mem0_client = get_mem0_client(settings)
    return MemoryService(mem0_client)


@router.post("/memories",
             response_model=MemoryResponse,
             summary="Store a memory",
             description="Store a new memory for a user")
@limiter.limit("30/minute")
async def store_memory(
    request: Request,
    memory_request: MemoryStoreRequest,
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    try:
        logger.info(f"Received store memory request: {memory_request}")
        result = await memory_service.store_memory(memory_request)
        logger.info(f"Successfully stored memory: {result}")
        return result
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(ve),
                "error_code": "MEMORY_STORE_VALIDATION_ERROR",
                "details": str(ve)
            }
        )
    except HTTPException as he:
        return JSONResponse(
            status_code=he.status_code,
            content={
                "success": False,
                "message": he.detail if isinstance(he.detail, str) else he.detail.get("message", "HTTP error"),
                "error_code": he.detail.get("error_code", "HTTP_ERROR") if isinstance(he.detail, dict) else "HTTP_ERROR",
                "details": he.detail
            }
        )
    except Exception as e:
        logger.error(f"Failed to store memory: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to store memory",
                "error_code": "MEMORY_STORE_FAILED",
                "details": str(e)
            }
        )


@router.post("/memories/search",
             response_model=MemorySearchResponse,
             summary="Search memories",
             description="Search and retrieve memories for a user based on a query")
@limiter.limit("30/minute")
async def search_memories(
    request: Request,
    search_request: MemoryRetrieveRequest,
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemorySearchResponse:
    try:
        result = await memory_service.retrieve_memories(search_request)
        return result
    except ValueError as ve:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(ve),
                "error_code": "MEMORY_SEARCH_VALIDATION_ERROR",
                "details": str(ve)
            }
        )
    except HTTPException as he:
        return JSONResponse(
            status_code=he.status_code,
            content={
                "success": False,
                "message": he.detail if isinstance(he.detail, str) else he.detail.get("message", "HTTP error"),
                "error_code": he.detail.get("error_code", "HTTP_ERROR") if isinstance(he.detail, dict) else "HTTP_ERROR",
                "details": he.detail
            }
        )
    except Exception as e:
        logger.error(f"Failed to search memories for user {search_request.username}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to search memories",
                "error_code": "MEMORY_SEARCH_FAILED",
                "details": str(e)
            }
        )


@router.get("/memories/{username}",
            response_model=MemorySearchResponse,
            summary="Get all user memories",
            description="Retrieve all memories for a specific user")
@limiter.limit("30/minute")
async def get_user_memories(
    request: Request,
    username: str,
    limit: int = 10,
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemorySearchResponse:
    try:
        if not username.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Username cannot be empty",
                    "error_code": "USERNAME_REQUIRED",
                    "username": username
                }
            )
        if limit < 1 or limit > 50:
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "message": "Limit must be between 1 and 50",
                    "error_code": "LIMIT_OUT_OF_RANGE",
                    "limit": limit
                }
            )
        result = await memory_service.get_user_memories(username.strip(), limit)
        return result
    except HTTPException as he:
        return JSONResponse(
            status_code=he.status_code,
            content={
                "success": False,
                "message": he.detail if isinstance(he.detail, str) else he.detail.get("message", "HTTP error"),
                "error_code": he.detail.get("error_code", "HTTP_ERROR") if isinstance(he.detail, dict) else "HTTP_ERROR",
                "details": he.detail
            }
        )
    except Exception as e:
        logger.error(f"Failed to get memories for user {username}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to get user memories",
                "error_code": "MEMORY_GET_FAILED",
                "details": str(e)
            }
        )


@router.delete("/memories/{username}",
               response_model=MemoryResponse,
               summary="Delete all user memories",
               description="Delete all memories for a specific user")
@limiter.limit("10/minute")
async def delete_user_memories(
    request: Request,
    username: str,
    memory_service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    try:
        if not username.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Username cannot be empty",
                    "error_code": "USERNAME_REQUIRED",
                    "username": username
                }
            )
        result = await memory_service.delete_user_memories(username.strip())
        return result
    except HTTPException as he:
        return JSONResponse(
            status_code=he.status_code,
            content={
                "success": False,
                "message": he.detail if isinstance(he.detail, str) else he.detail.get("message", "HTTP error"),
                "error_code": he.detail.get("error_code", "HTTP_ERROR") if isinstance(he.detail, dict) else "HTTP_ERROR",
                "details": he.detail
            }
        )
    except Exception as e:
        logger.error(f"Failed to delete memories for user {username}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to delete user memories",
                "error_code": "MEMORY_DELETE_FAILED",
                "details": str(e)
            }
        )


@router.get("/health",
            response_model=HealthResponse,
            summary="Health check",
            description="Check the health status of the memory service")
async def health_check() -> HealthResponse:
    try:
        settings = get_settings()
        mem0_status = "connected" if await health_check_mem0(settings) else "disconnected"
        status = "healthy" if mem0_status == "connected" else "unhealthy"
        return HealthResponse(
            status=status,
            service=settings.SERVICE_NAME,
            mem0=mem0_status,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Health check failed",
                "error_code": "HEALTH_CHECK_FAILED",
                "details": str(e)
            }
        )
