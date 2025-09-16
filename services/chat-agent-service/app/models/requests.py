from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CreateRoomRequest(BaseModel):
    room_name: str = Field(..., description="Name of the room to create")
    max_participants: Optional[int] = Field(default=10, description="Maximum number of participants")
    empty_timeout: Optional[int] = Field(default=300, description="Timeout in seconds when room is empty")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata for the room")

class JoinRoomRequest(BaseModel):
    room_name: str = Field(..., description="Name of the room to join")
    username: str = Field(..., description="Username of the participant")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata for the participant")

class SendMessageRequest(BaseModel):
    room_name: str = Field(..., description="Name of the room")
    username: str = Field(..., description="Username sending the message")
    message: str = Field(..., description="Message content")

class StartAgentRequest(BaseModel):
    room_name: str = Field(..., description="Name of the room to start agent in")

class StopAgentRequest(BaseModel):
    room_name: str = Field(..., description="Name of the room to stop agent in")