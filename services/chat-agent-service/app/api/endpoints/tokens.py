from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timedelta
import logging
from fastapi.responses import JSONResponse

from app.models.requests import JoinRoomRequest
from app.models.responses import TokenResponse
from app.services.agent_manager import AgentManager

router = APIRouter()
logger = logging.getLogger(__name__)

def get_agent_manager(request: Request) -> AgentManager:
    return request.app.state.agent_manager

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timedelta
import logging

from app.models.requests import JoinRoomRequest
from app.models.responses import TokenResponse
from app.services.agent_manager import AgentManager

router = APIRouter()
logger = logging.getLogger(__name__)

def get_agent_manager(request: Request) -> AgentManager:
    if not hasattr(request.app.state, 'agent_manager'):
        raise HTTPException(
            status_code=500,
            detail="Agent manager not initialized"
        )
    return request.app.state.agent_manager

@router.post("/generate", response_model=TokenResponse)
async def generate_token(
    request: JoinRoomRequest,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    try:
        if not request.room_name or len(request.room_name.strip()) == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Room name cannot be empty",
                    "error_code": "ROOM_NAME_REQUIRED",
                    "room_name": request.room_name
                }
            )
        if not request.username or len(request.username.strip()) == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Username cannot be empty",
                    "error_code": "USERNAME_REQUIRED",
                    "username": request.username
                }
            )
        try:
            await agent_manager.livekit_client.get_room(request.room_name)
        except ValueError:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"Room '{request.room_name}' does not exist",
                    "error_code": "ROOM_NOT_FOUND",
                    "room_name": request.room_name
                }
            )
        expires_at = datetime.now() + timedelta(hours=24)
        token = await agent_manager.livekit_client.generate_access_token(
            room_name=request.room_name,
            username=request.username,
            metadata=request.metadata
        )
        return TokenResponse(
            success=True,
            message="Access token generated successfully",
            token=token,
            room_name=request.room_name,
            username=request.username,
            expires_at=expires_at
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
        logger.error(f"Error generating token for {request.username}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to generate access token",
                "error_code": "TOKEN_GENERATION_FAILED",
                "username": request.username,
                "room_name": request.room_name,
                "details": str(e)
            }
        )

@router.post("/validate")
async def validate_token(
    token: str,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    try:
        is_valid = await agent_manager.livekit_client.validate_token(token)
        return {
            "success": True,
            "message": "Token validation completed",
            "valid": is_valid,
            "timestamp": datetime.now()
        }
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
        logger.error(f"Error validating token: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to validate token",
                "error_code": "TOKEN_VALIDATION_FAILED",
                "details": str(e)
            }
        )