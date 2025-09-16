from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import List
import logging
import re

from app.models.requests import CreateRoomRequest, JoinRoomRequest, SendMessageRequest
from app.models.responses import RoomResponse, MessageResponse, RoomListResponse, ErrorResponse
from app.services.livekit_client import LiveKitClient
from app.services.agent_manager import AgentManager
from app.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_ROOM_NAME_LENGTH = 100
MIN_ROOM_NAME_LENGTH = 1
MAX_PARTICIPANTS = 1000
MIN_PARTICIPANTS = 1
MAX_EMPTY_TIMEOUT = 86400  
MIN_EMPTY_TIMEOUT = 10     
MAX_METADATA_SIZE = 1024  

def get_agent_manager(request: Request) -> AgentManager:
    return request.app.state.agent_manager

def validate_room_name(room_name: str) -> tuple[bool, str]:
    """Validate room name format and length"""
    if not room_name or not isinstance(room_name, str):
        return False, "Room name must be a non-empty string"
    
    room_name = room_name.strip()
    
    if len(room_name) < MIN_ROOM_NAME_LENGTH:
        return False, f"Room name must be at least {MIN_ROOM_NAME_LENGTH} character(s)"
    
    if len(room_name) > MAX_ROOM_NAME_LENGTH:
        return False, f"Room name cannot exceed {MAX_ROOM_NAME_LENGTH} characters"
    
    if not re.match(r'^[a-zA-Z0-9\-_\s]+$', room_name):
        return False, "Room name can only contain letters, numbers, hyphens, underscores, and spaces"
    
    return True, ""

def validate_participants_count(count: int) -> tuple[bool, str]:
    if not isinstance(count, int):
        return False, "Max participants must be an integer"
    
    if count < MIN_PARTICIPANTS:
        return False, f"Max participants must be at least {MIN_PARTICIPANTS}"
    
    if count > MAX_PARTICIPANTS:
        return False, f"Max participants cannot exceed {MAX_PARTICIPANTS}"
    
    return True, ""

def validate_empty_timeout(timeout: int) -> tuple[bool, str]:
    if not isinstance(timeout, int):
        return False, "Empty timeout must be an integer"
    
    if timeout < MIN_EMPTY_TIMEOUT:
        return False, f"Empty timeout must be at least {MIN_EMPTY_TIMEOUT} seconds"
    
    if timeout > MAX_EMPTY_TIMEOUT:
        return False, f"Empty timeout cannot exceed {MAX_EMPTY_TIMEOUT} seconds ({MAX_EMPTY_TIMEOUT//3600} hours)"
    
    return True, ""

def validate_metadata(metadata) -> tuple[bool, str]:
    if metadata is None:
        return True, ""
    
    if not isinstance(metadata, dict):
        return False, "Metadata must be a dictionary"
    
    metadata_str = str(metadata)
    if len(metadata_str) > MAX_METADATA_SIZE:
        return False, f"Metadata size cannot exceed {MAX_METADATA_SIZE} characters"
    
    return True, ""

@router.post("/create", response_model=RoomResponse)
async def create_room(
    request: CreateRoomRequest,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    try:
        is_valid, error_msg = validate_room_name(request.room_name)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": error_msg,
                    "error_code": "INVALID_ROOM_NAME",
                    "room_name": request.room_name[:100] if request.room_name else None  
                }
            )
        
        is_valid, error_msg = validate_participants_count(request.max_participants)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": error_msg,
                    "error_code": "INVALID_MAX_PARTICIPANTS",
                    "max_participants": request.max_participants
                }
            )
        
        is_valid, error_msg = validate_empty_timeout(request.empty_timeout)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": error_msg,
                    "error_code": "INVALID_EMPTY_TIMEOUT",
                    "empty_timeout": request.empty_timeout
                }
            )
        
        is_valid, error_msg = validate_metadata(request.metadata)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": error_msg,
                    "error_code": "INVALID_METADATA"
                }
            )
        
        clean_room_name = request.room_name.strip()
        
        try:
            existing_room = await agent_manager.livekit_client.get_room(clean_room_name)
            if existing_room:
                return JSONResponse(
                    status_code=409,
                    content={
                        "success": False,
                        "message": f"Room '{clean_room_name}' already exists",
                        "error_code": "ROOM_EXISTS",
                        "room_name": clean_room_name,
                        "room_sid": existing_room.get("sid")
                    }
                )
        except ValueError:
            pass
        except Exception as e:
            logger.error(f"Error checking if room exists: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Failed to check room existence",
                    "error_code": "ROOM_CHECK_FAILED"
                }
            )
        
        room_info = await agent_manager.livekit_client.create_room(
            room_name=clean_room_name,
            max_participants=request.max_participants,
            empty_timeout=request.empty_timeout,
            metadata=request.metadata
        )
        
        return RoomResponse(
            success=True,
            message="Room created successfully",
            room_name=clean_room_name,
            room_sid=room_info.get("sid"),
            metadata=request.metadata
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
        logger.error(f"Error creating room: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to create room due to internal error",
                "error_code": "ROOM_CREATION_FAILED",
                "details": "Internal server error"  
            }
        )

@router.get("/list", response_model=RoomListResponse)
async def list_rooms(
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    try:
        rooms = await agent_manager.livekit_client.list_rooms()
        return RoomListResponse(
            success=True,
            message="Rooms retrieved successfully",
            rooms=rooms,
            total_count=len(rooms)
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
        logger.error(f"Error listing rooms: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to list rooms",
                "error_code": "ROOM_LIST_FAILED",
                "details": str(e)
            }
        )

@router.get("/{room_name}", response_model=RoomResponse)
async def get_room(
    room_name: str,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    try:
        is_valid, error_msg = validate_room_name(room_name)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": error_msg,
                    "error_code": "INVALID_ROOM_NAME",
                    "room_name": room_name[:100] if room_name else None
                }
            )
        
        clean_room_name = room_name.strip()
        room_info = await agent_manager.livekit_client.get_room(clean_room_name)
        return RoomResponse(
            success=True,
            message="Room information retrieved successfully",
            room_name=clean_room_name,
            room_sid=room_info.get("sid"),
            participants_count=room_info.get("num_participants", 0),
            metadata=room_info.get("metadata")
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
        logger.error(f"Error getting room info: {str(e)}")
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
                "details": "Room does not exist"  
            }
        )

@router.delete("/{room_name}")
async def delete_room(
    room_name: str,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    try:
        is_valid, error_msg = validate_room_name(room_name)
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": error_msg,
                    "error_code": "INVALID_ROOM_NAME",
                    "room_name": room_name[:100] if room_name else None
                }
            )
        
        clean_room_name = room_name.strip()
        await agent_manager.livekit_client.delete_room(clean_room_name)
        return RoomResponse(
            success=True,
            message="Room deleted successfully",
            room_name=clean_room_name
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
        logger.error(f"Error deleting room: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to delete room",
                "error_code": "ROOM_DELETE_FAILED",
                "details": "Internal server error"  
            }
        )