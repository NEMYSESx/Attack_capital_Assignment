import httpx
import logging
from typing import Dict, Any, List, Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

class MemoryClient:
    def __init__(self):
        self.base_url = settings.MEMORY_SERVICE_URL
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def add_memory(
        self, 
        user_id: str, 
        message: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            payload = {
                "user_id": user_id,
                "message": message,
                "metadata": metadata or {}
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/memory/add",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Added memory for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error adding memory for user {user_id}: {str(e)}")
            raise
    
    async def get_memories(
        self, 
        user_id: str, 
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        try:
            params = {
                "user_id": user_id,
                "limit": limit
            }
            
            if query:
                params["query"] = query
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/memory/get",
                params=params
            )
            response.raise_for_status()
            
            result = response.json()
            memories = result.get("memories", [])
            
            logger.info(f"Retrieved {len(memories)} memories for user {user_id}")
            return memories
            
        except Exception as e:
            logger.error(f"Error retrieving memories for user {user_id}: {str(e)}")
            raise
    
    async def search_memories(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        try:
            payload = {
                "user_id": user_id,
                "query": query,
                "limit": limit
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/memory/search",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            memories = result.get("memories", [])
            
            logger.info(f"Found {len(memories)} relevant memories for user {user_id}")
            return memories
            
        except Exception as e:
            logger.error(f"Error searching memories for user {user_id}: {str(e)}")
            raise
    
    async def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/memory/all",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            
            result = response.json()
            memories = result.get("memories", [])
            
            logger.info(f"Retrieved all {len(memories)} memories for user {user_id}")
            return memories
            
        except Exception as e:
            logger.error(f"Error retrieving all memories for user {user_id}: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Memory service health check failed: {str(e)}")
            return False