import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from livekit.api import LiveKitAPI, AccessToken, VideoGrants
from livekit import api 
import json

from app.config.settings import settings

logger = logging.getLogger(__name__)

class LiveKitClient:
    def __init__(self):
        self.api_key = settings.LIVEKIT_API_KEY
        self.api_secret = settings.LIVEKIT_API_SECRET
        self.livekit_url = settings.LIVEKIT_URL
        
        self.lkapi = LiveKitAPI(self.livekit_url, api_key=self.api_key, api_secret=self.api_secret)
        self.room_service = self.lkapi.room
        
    async def create_room(
        self, 
        room_name: str, 
        max_participants: int = 10,
        empty_timeout: int = 300,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            room_create_options = api.CreateRoomRequest(
                name=room_name,
                empty_timeout=empty_timeout,
                max_participants=max_participants,
                metadata=json.dumps(metadata) if metadata else None
            )
            
            room = await self.room_service.create_room(room_create_options)
            
            logger.info(f"Created room: {room_name}")
            return {
                "name": room.name,
                "sid": room.sid,
                "max_participants": room.max_participants,
                "creation_time": room.creation_time,
                "metadata": json.loads(room.metadata) if room.metadata else None
            }
            
        except Exception as e:
            logger.error(f"Error creating room {room_name}: {str(e)}")
            raise
    
    async def list_rooms(self) -> List[Dict[str, Any]]:
        try:
            rooms = await self.room_service.list_rooms(api.ListRoomsRequest())
            
            room_list = []
            for room in rooms.rooms:
                room_info = {
                    "name": room.name,
                    "sid": room.sid,
                    "num_participants": room.num_participants,
                    "creation_time": room.creation_time,
                    "metadata": json.loads(room.metadata) if room.metadata else None
                }
                room_list.append(room_info)
            
            return room_list
            
        except Exception as e:
            logger.error(f"Error listing rooms: {str(e)}")
            raise
    
    async def get_room(self, room_name: str) -> Dict[str, Any]:
        try:
            rooms = await self.room_service.list_rooms(
                api.ListRoomsRequest(names=[room_name])
            )
            
            if not rooms.rooms:
                raise ValueError(f"Room {room_name} not found")
            
            room = rooms.rooms[0]
            return {
                "name": room.name,
                "sid": room.sid,
                "num_participants": room.num_participants,
                "creation_time": room.creation_time,
                "metadata": json.loads(room.metadata) if room.metadata else None
            }
            
        except Exception as e:
            logger.error(f"Error getting room {room_name}: {str(e)}")
            raise
    
    async def delete_room(self, room_name: str):
        try:
            await self.room_service.delete_room(
                api.DeleteRoomRequest(room=room_name)
            )
            logger.info(f"Deleted room: {room_name}")
            
        except Exception as e:
            logger.error(f"Error deleting room {room_name}: {str(e)}")
            raise
    
    async def generate_access_token(
        self, 
        room_name: str, 
        username: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        try:
            token = AccessToken(self.api_key, self.api_secret)
            token = token.with_grants(VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True
            ))
            token.identity = username
            
            if metadata:
                token.metadata = json.dumps(metadata)
            
            token.ttl = timedelta(hours=24)
            
            jwt_token = token.to_jwt()
            logger.info(f"Generated token for user {username} in room {room_name}")
            
            return jwt_token
            
        except Exception as e:
            logger.error(f"Error generating token for {username}: {str(e)}")
            raise
    
    async def validate_token(self, token: str) -> bool:
        try:
            access_token = AccessToken.from_jwt(token, self.api_secret)
            return access_token is not None
            
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return False
    
    async def get_participants(self, room_name: str) -> List[Dict[str, Any]]:
        try:
            participants = await self.room_service.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )
            
            participant_list = []
            for participant in participants.participants:
                participant_info = {
                    "sid": participant.sid,
                    "identity": participant.identity,
                    "name": participant.name,
                    "state": participant.state,
                    "joined_at": participant.joined_at,
                    "metadata": json.loads(participant.metadata) if participant.metadata else None
                }
                participant_list.append(participant_info)
            
            return participant_list
            
        except Exception as e:
            logger.error(f"Error getting participants for room {room_name}: {str(e)}")
            raise