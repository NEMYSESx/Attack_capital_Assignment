import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from livekit import rtc
from livekit.rtc import Room, DataPacket

from app.services.livekit_client import LiveKitClient
from app.services.memory_client import MemoryClient
from app.services.llm_client import LLMClient
from app.config.settings import settings

logger = logging.getLogger(__name__)

class ChatAgent:
    def __init__(
        self, 
        room_name: str,
        livekit_client: LiveKitClient,
        memory_client: MemoryClient,
        llm_client: LLMClient
    ):
        self.room_name = room_name
        self.livekit_client = livekit_client
        self.memory_client = memory_client
        self.llm_client = llm_client
        
        self.agent_name = settings.AGENT_NAME
        self.agent_username = f"{self.agent_name.lower().replace(' ', '_')}_agent"
        
        self.room: Optional[Room] = None
        self.participant_id: Optional[str] = None
        self._running = False
        
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
    
    async def start(self):
        if self._running:
            logger.warning(f"Agent already running in room {self.room_name}")
            return
        
        try:
            logger.info(f"Starting chat agent in room {self.room_name}")
            
            token = await self.livekit_client.generate_access_token(
                room_name=self.room_name,
                username=self.agent_username,
                metadata={"type": "ai_agent", "name": self.agent_name}
            )
            
            self.room = rtc.Room()
            
            self._setup_event_handlers()
            
            await self.room.connect(settings.LIVEKIT_URL, token)
            
            self._running = True
            logger.info(f"Chat agent connected to room {self.room_name}")
            
        except Exception as e:
            logger.error(f"Error starting chat agent: {str(e)}")
            await self._cleanup()
            raise
    
    async def stop(self):
        if not self._running:
            return
        
        logger.info(f"Stopping chat agent in room {self.room_name}")
        self._running = False
        await self._cleanup()
    
    def is_connected(self) -> bool:
        return self.room is not None and self.room.connection_state == rtc.ConnectionState.CONN_CONNECTED
    
    async def _cleanup(self):
        if self.room:
            await self.room.disconnect()
            self.room = None
        self.participant_id = None
    
    def _setup_event_handlers(self):
        
        @self.room.on("connected")
        def on_connected():
            logger.info(f"Agent connected to room {self.room_name}")
            self.participant_id = self.room.local_participant.sid
        
        @self.room.on("disconnected")
        def on_disconnected():
            logger.info(f"Agent disconnected from room {self.room_name}")
            self._running = False
        
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"Participant {participant.identity} joined room {self.room_name}")
            asyncio.create_task(self._send_greeting(participant.identity))
        
        @self.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"Participant {participant.identity} left room {self.room_name}")
        
        @self.room.on("data_received")
        def on_data_received(data: rtc.DataPacket, participant: rtc.RemoteParticipant):
            asyncio.create_task(self._handle_message(data, participant))
    
    async def _send_greeting(self, username: str):
        try:
            memories = await self.memory_client.get_memories(username, limit=3)
            
            if memories:
                context = await self.llm_client.generate_context_summary(memories)
                system_prompt = self.llm_client.get_system_prompt(self.agent_name)
                
                messages = [{
                    "role": "user", 
                    "content": f"A user named {username} just joined the chat room. Greet them warmly and reference something from your previous conversations if appropriate."
                }]
                
                greeting = await self.llm_client.generate_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    context=context
                )
            else:
                greeting = f"Hello {username}! 👋 Welcome to the chat room! I'm {self.agent_name}, your AI assistant. How can I help you today?"
            
            await self._send_message(greeting)
            
        except Exception as e:
            logger.error(f"Error sending greeting: {str(e)}")
            await self._send_message(f"Hello {username}! Welcome to the chat room!")
    
    async def _handle_message(self, data: rtc.DataPacket, participant: rtc.RemoteParticipant):
        try:
            if participant.identity == self.agent_username:
                return
            
            message_data = json.loads(data.data.decode('utf-8'))
            message_text = message_data.get('message', '').strip()
            username = participant.identity
            
            if not message_text:
                return
            
            logger.info(f"Received message from {username}: {message_text}")
            
            if username not in self.conversation_history:
                self.conversation_history[username] = []
            
            self.conversation_history[username].append({
                "role": "user",
                "content": message_text,
                "timestamp": datetime.now().isoformat()
            })
            
            await self.memory_client.add_memory(
                user_id=username,
                message=message_text,
                metadata={
                    "room": self.room_name,
                    "timestamp": datetime.now().isoformat(),
                    "type": "user_message"
                }
            )
            
            response = await self._generate_response(username, message_text)
            
            if response:
                self.conversation_history[username].append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
                
                await self.memory_client.add_memory(
                    user_id=username,
                    message=f"AI Assistant: {response}",
                    metadata={
                        "room": self.room_name,
                        "timestamp": datetime.now().isoformat(),
                        "type": "ai_response"
                    }
                )
                
                await self._send_message(response)
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
    
    async def _generate_response(self, username: str, message: str) -> Optional[str]:
        try:
            relevant_memories = await self.memory_client.search_memories(
                user_id=username,
                query=message,
                limit=5
            )
            
            context = await self.llm_client.generate_context_summary(relevant_memories)
            
            messages = []
            
            if username in self.conversation_history:
                recent_history = self.conversation_history[username][-6:]
                for msg in recent_history:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            if not messages or messages[-1]["content"] != message:
                messages.append({
                    "role": "user",
                    "content": message
                })
            
            system_prompt = self.llm_client.get_system_prompt(self.agent_name)
            
            response = await self.llm_client.generate_response(
                messages=messages,
                system_prompt=system_prompt,
                context=context
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I'm sorry, I encountered an error while processing your message. Could you please try again?"
    
    async def _send_message(self, message: str):
        try:
            if not self.room or not self.is_connected():
                logger.warning("Cannot send message - agent not connected to room")
                return
            
            message_data = {
                "message": message,
                "sender": self.agent_username,
                "timestamp": datetime.now().isoformat(),
                "type": "chat"
            }
            
            data_packet = rtc.DataPacket(
                data=json.dumps(message_data).encode('utf-8'),
                kind=rtc.DataPacketKind.KIND_RELIABLE
            )
            
            await self.room.local_participant.publish_data(data_packet)
            logger.info(f"Sent message: {message}")
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
