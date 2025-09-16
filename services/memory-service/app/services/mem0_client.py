import logging
from typing import Optional
from mem0 import MemoryClient
from app.config.settings import Settings

logger = logging.getLogger(__name__)

_mem0_client: Optional[MemoryClient] = None


def create_mem0_client(settings: Settings) -> MemoryClient:
    try:
        if not settings.MEM0_API_KEY:
            raise ValueError("MEM0_API_KEY is required for hosted mem0 service")
        
        client = MemoryClient(api_key=settings.MEM0_API_KEY)
        
        logger.info("mem0 hosted client created successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create mem0 client: {str(e)}")
        raise Exception(f"mem0 client creation failed: {str(e)}")


def get_mem0_client(settings: Settings) -> MemoryClient:
    global _mem0_client
    
    if _mem0_client is None:
        _mem0_client = create_mem0_client(settings)
    
    return _mem0_client


def close_mem0_client():
    global _mem0_client
    
    if _mem0_client:
        _mem0_client = None
        logger.info("mem0 client connection closed")


async def health_check_mem0(settings: Settings) -> bool:
    try:
        client = get_mem0_client(settings)
        client.get_all(user_id="health_check", limit=1)
        return True
    except Exception as e:
        logger.error(f"mem0 health check failed: {str(e)}")
        return False