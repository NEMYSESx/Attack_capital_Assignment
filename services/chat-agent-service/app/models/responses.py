from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class BaseResponse(BaseModel):
    success: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class RoomResponse(BaseResponse):
    room_name: str
    room_sid: Optional[str] = None
    participants_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

class TokenResponse(BaseResponse):
    token: str
    room_name: str
    username: str
    expires_at: datetime

class AgentStatusResponse(BaseResponse):
    room_name: str
    agent_active: bool
    agent_participant_id: Optional[str] = None

class MessageResponse(BaseResponse):
    room_name: str
    username: str
    message: str
    message_id: str

class RoomListResponse(BaseResponse):
    rooms: List[Dict[str, Any]]
    total_count: int

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
