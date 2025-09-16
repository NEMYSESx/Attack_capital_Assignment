import asyncio
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from app.services.livekit_client import LiveKitClient
from app.services.memory_client import MemoryClient
from app.services.llm_client import LLMClient
from app.services.chat_agent import ChatAgent
from app.config.settings import settings

logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self):
        self.livekit_client = LiveKitClient()
        self.memory_client = MemoryClient()
        self.llm_client = LLMClient()
        
        self.active_agents: Dict[str, ChatAgent] = {}
        self._initialized = False
    
    async def initialize(self):
        if self._initialized:
            return
        
        logger.info("Initializing Agent Manager...")
        
        try:
            memory_healthy = await self.memory_client.health_check()
            if not memory_healthy:
                logger.warning("Memory service is not healthy")
            
            logger.info("Agent Manager initialized successfully")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Agent Manager: {str(e)}")
            raise
    
    async def cleanup(self):
        logger.info("Cleaning up Agent Manager...")
        
        for room_name in list(self.active_agents.keys()):
            try:
                await self.stop_agent(room_name)
            except Exception as e:
                logger.error(f"Error stopping agent in room {room_name}: {str(e)}")
        
        await self.memory_client.close()
        
        logger.info("Agent Manager cleanup completed")
    
    async def start_agent(self, room_name: str) -> Dict[str, Any]:
        if room_name in self.active_agents:
            logger.warning(f"Agent already active in room {room_name}")
            return {
                "participant_id": self.active_agents[room_name].participant_id,
                "status": "already_active"
            }
        
        try:
            agent = ChatAgent(
                room_name=room_name,
                livekit_client=self.livekit_client,
                memory_client=self.memory_client,
                llm_client=self.llm_client
            )
            
            await agent.start()
            
            self.active_agents[room_name] = agent
            
            logger.info(f"Started agent in room {room_name}")
            return {
                "participant_id": agent.participant_id,
                "status": "started"
            }
            
        except Exception as e:
            logger.error(f"Error starting agent in room {room_name}: {str(e)}")
            raise
    
    async def stop_agent(self, room_name: str):
        if room_name not in self.active_agents:
            logger.warning(f"No active agent in room {room_name}")
            return
        
        try:
            agent = self.active_agents[room_name]
            await agent.stop()
            
            del self.active_agents[room_name]
            
            logger.info(f"Stopped agent in room {room_name}")
            
        except Exception as e:
            logger.error(f"Error stopping agent in room {room_name}: {str(e)}")
            raise
    
    async def get_agent_status(self, room_name: str) -> Dict[str, Any]:
        if room_name in self.active_agents:
            agent = self.active_agents[room_name]
            return {
                "active": True,
                "participant_id": agent.participant_id,
                "connected": agent.is_connected(),
                "room_name": room_name
            }
        else:
            return {
                "active": False,
                "participant_id": None,
                "connected": False,
                "room_name": room_name
            }
