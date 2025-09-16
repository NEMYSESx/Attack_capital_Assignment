import logging
from datetime import datetime
from typing import List, Dict, Any
from mem0 import MemoryClient

from app.models.requests import MemoryStoreRequest, MemoryRetrieveRequest
from app.models.responses import Memory, MemoryResponse, MemorySearchResponse

logger = logging.getLogger(__name__)


class MemoryService:
    
    def __init__(self, mem0_client: MemoryClient):
        self.mem0_client = mem0_client
        logger.info("MemoryService initialized")
    
    async def store_memory(self, request: MemoryStoreRequest) -> MemoryResponse:
        try:
            if not request.username.strip():
                raise ValueError("Username cannot be empty")
            
            if not request.message.strip():
                raise ValueError("Message cannot be empty")
            
            logger.info(f"Storing memory for user: {request.username}")
            
            metadata = request.metadata or {}
            metadata.update({
                "stored_at": datetime.utcnow().isoformat(),
                "username": request.username,
                "service": "memory-service"
            })
            
            try:
                logger.debug(f"Calling mem0 add with user_id: {request.username}, message: {request.message}")
                messages = [{"role": "user", "content": request.message.strip()}]
                logger.debug(f"Messages to store: {messages}")
                logger.debug(f"Metadata: {metadata}")
                
                result = self.mem0_client.add(
                    messages=messages,
                    user_id=request.username.strip(),
                    metadata=metadata
                )
                
                logger.debug(f"mem0 add result: {result}")
                
                if isinstance(result, list):
                    logger.warning(f"Unexpected list response from mem0 add: {result}")
                    if len(result) > 0 and isinstance(result[0], dict):
                        memory_id = result[0].get("id", "unknown")
                    else:
                        memory_id = "unknown"
                else:
                    memory_id = result.get("id", "unknown") if result else "unknown"
                    
            except Exception as e:
                logger.error(f"Error in mem0 add: {str(e)}", exc_info=True)
                raise Exception(f"Failed to add memory to mem0: {str(e)}")
            
            if memory_id == "unknown":
                logger.warning(f"Memory stored but ID not returned for user: {request.username}")
            
            logger.info(f"Memory stored successfully for user: {request.username}, ID: {memory_id}")
            
            return MemoryResponse(
                success=True,
                message="Memory stored successfully",
                data={
                    "memory_id": memory_id, 
                    "username": request.username,
                    "stored_at": metadata["stored_at"]
                }
            )
            
        except ValueError as ve:
            logger.error(f"Validation error for user {request.username}: {str(ve)}")
            raise ve
        except Exception as e:
            logger.error(f"Failed to store memory for user {request.username}: {str(e)}")
            raise Exception(f"Failed to store memory: {str(e)}")
    
    async def retrieve_memories(self, request: MemoryRetrieveRequest) -> MemorySearchResponse:
        try:
            if not request.username.strip():
                raise ValueError("Username cannot be empty")
            
            if not request.query.strip():
                raise ValueError("Query cannot be empty")
            
            if request.limit < 1 or request.limit > 20:
                raise ValueError("Limit must be between 1 and 20")
            
            logger.info(f"Retrieving memories for user: {request.username} with query: {request.query}")
            
            try:
                logger.debug(f"Calling mem0 search with query: {request.query}, user_id: {request.username}, limit: {request.limit}")
                results = self.mem0_client.search(
                    query=request.query.strip(),
                    user_id=request.username.strip(),
                    limit=request.limit
                )
                logger.debug(f"mem0 search results: {results}")
                
                memories = self._format_memories(results)
                
                logger.info(f"Retrieved {len(memories)} memories for user: {request.username}")
                
                return MemorySearchResponse(
                    success=True,
                    message=f"Found {len(memories)} memories for query: '{request.query}'",
                    memories=memories,
                    count=len(memories)
                )
                
            except Exception as e:
                logger.error(f"Error in mem0 search: {str(e)}", exc_info=True)
                raise Exception(f"mem0 search failed: {str(e)}")
            
        except ValueError as ve:
            logger.error(f"Validation error for user {request.username}: {str(ve)}")
            raise ve
        except Exception as e:
            logger.error(f"Failed to retrieve memories for user {request.username}", exc_info=True)
            raise Exception(f"Failed to retrieve memories: {str(e)}")
    
    async def get_user_memories(self, username: str, limit: int = 10) -> MemorySearchResponse:
        try:
            if not username.strip():
                raise ValueError("Username cannot be empty")
            
            if limit < 1 or limit > 50:
                raise ValueError("Limit must be between 1 and 50")
            
            username = username.strip()
            logger.info(f"Getting all memories for user: {username}")
            
            results = self.mem0_client.get_all(user_id=username, limit=limit)
            
            memories = self._format_memories(results)
            
            logger.info(f"Retrieved {len(memories)} total memories for user: {username}")
            
            return MemorySearchResponse(
                success=True,
                message=f"Retrieved all memories for user: {username}",
                memories=memories,
                count=len(memories)
            )
            
        except ValueError as ve:
            logger.error(f"Validation error for user {username}: {str(ve)}")
            raise ve
        except Exception as e:
            logger.error(f"Failed to get memories for user {username}: {str(e)}")
            raise Exception(f"Failed to get user memories: {str(e)}")
    
    async def delete_user_memories(self, username: str) -> MemoryResponse:
        try:
            if not username.strip():
                raise ValueError("Username cannot be empty")
            
            username = username.strip()
            logger.info(f"Deleting all memories for user: {username}")
            
            result = self.mem0_client.delete_all(user_id=username)
            
            deleted_count = result.get("deleted_count", 0) if result else 0
            
            logger.info(f"Deleted {deleted_count} memories for user: {username}")
            
            return MemoryResponse(
                success=True,
                message=f"Deleted {deleted_count} memories for user: {username}",
                data={
                    "deleted_count": deleted_count, 
                    "username": username,
                    "deleted_at": datetime.utcnow().isoformat()
                }
            )
            
        except ValueError as ve:
            logger.error(f"Validation error for user {username}: {str(ve)}")
            raise ve
        except Exception as e:
            logger.error(f"Failed to delete memories for user {username}: {str(e)}")
            raise Exception(f"Failed to delete user memories: {str(e)}")
    
    def _format_memories(self, mem0_results: List[Dict[str, Any]]) -> List[Memory]:
        memories = []
        
        if not mem0_results:
            logger.info("No memories found in results")
            return memories
        
        for i, memory_data in enumerate(mem0_results):
            try:
                memory_id = memory_data.get("id", f"unknown_{i}")
                memory_text = (
                    memory_data.get("text") or 
                    memory_data.get("content") or 
                    memory_data.get("memory", "")
                )
                
                if not memory_text:
                    logger.warning(f"Empty memory text found in result {i}: {memory_data}")
                    continue
                
                memory = Memory(
                    id=memory_id,
                    text=memory_text,
                    score=memory_data.get("score"),
                    metadata=memory_data.get("metadata", {})
                )
                memories.append(memory)
                
            except Exception as e:
                logger.warning(f"Failed to format memory {i}: {memory_data}, error: {str(e)}")
                continue
        
        logger.info(f"Successfully formatted {len(memories)} memories")
        return memories