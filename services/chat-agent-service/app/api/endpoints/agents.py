from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import logging

from fastapi import Request as FastAPIRequest
import json
from fastapi.encoders import jsonable_encoder
from json.decoder import JSONDecodeError

from app.models.requests import StartAgentRequest, StopAgentRequest
from app.models.responses import AgentStatusResponse
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

@router.post("/start", response_model=AgentStatusResponse)
async def start_agent(
    request: StartAgentRequest,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    try:
        if not isinstance(request, StartAgentRequest):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Malformed JSON in request body.",
                    "error_code": "INVALID_JSON"
                }
            )
    except JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Malformed JSON in request body.",
                "error_code": "INVALID_JSON"
            }
        )
    try:
        if not request.room_name or len(request.room_name.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Room name cannot be empty"
            )
        
        try:
            await agent_manager.livekit_client.get_room(request.room_name)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Room '{request.room_name}' does not exist. Please create the room first."
            )
        
        agent_info = await agent_manager.start_agent(request.room_name)
        
        return AgentStatusResponse(
            success=True,
            message=f"Agent started successfully in room {request.room_name}",
            room_name=request.room_name,
            agent_active=True,
            agent_participant_id=agent_info.get("participant_id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting agent in room {request.room_name}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "message": "Failed to start agent due to internal error",
                "error_code": "AGENT_START_FAILED",
                "room_name": request.room_name
            }
        )

@router.post("/stop", response_model=AgentStatusResponse)
async def stop_agent(
    request: StopAgentRequest,
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
        status = await agent_manager.get_agent_status(request.room_name)
        if not status.get("active", False):
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"No active agent found in room {request.room_name}",
                    "room_name": request.room_name,
                    "agent_active": False,
                    "agent_participant_id": None
                }
            )
        await agent_manager.stop_agent(request.room_name)
        return AgentStatusResponse(
            success=True,
            message=f"Agent stopped successfully in room {request.room_name}",
            room_name=request.room_name,
            agent_active=False
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
        logger.error(f"Error stopping agent in room {request.room_name}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to stop agent due to internal error",
                "error_code": "AGENT_STOP_FAILED",
                "room_name": request.room_name,
                "details": str(e)
            }
        )

@router.get("/status/{room_name}", response_model=AgentStatusResponse)
async def get_agent_status(
    room_name: str,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    try:
        if not room_name or len(room_name.strip()) == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Room name cannot be empty",
                    "error_code": "ROOM_NAME_REQUIRED",
                    "room_name": room_name
                }
            )
        status = await agent_manager.get_agent_status(room_name)
        return AgentStatusResponse(
            success=True,
            message="Agent status retrieved successfully",
            room_name=room_name,
            agent_active=status.get("active", False),
            agent_participant_id=status.get("participant_id"),
            agent_connected=status.get("connected", False)
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
        logger.error(f"Error getting agent status for room {room_name}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to get agent status",
                "error_code": "AGENT_STATUS_FAILED",
                "room_name": room_name,
                "details": str(e)
            }
        )