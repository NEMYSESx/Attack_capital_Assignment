from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class MemoryResponse(BaseModel):
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Memory stored successfully",
                "data": {
                    "memory_id": "mem_123",
                    "username": "john_doe",
                    "stored_at": "2024-01-15T10:30:00.000Z"
                }
            }
        }
    }


class Memory(BaseModel):
    id: str = Field(..., description="Memory ID")
    text: str = Field(..., description="Memory content")
    score: Optional[float] = Field(default=None, description="Similarity score (for search results)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Memory metadata")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "mem_123",
                "text": "User loves playing chess on weekends",
                "score": 0.95,
                "metadata": {
                    "timestamp": "2024-01-15T10:30:00",
                    "username": "john_doe"
                }
            }
        }
    }


class MemorySearchResponse(BaseModel):
    success: bool = Field(..., description="Whether search was successful")
    message: str = Field(..., description="Response message")
    memories: List[Memory] = Field(default_factory=list, description="Retrieved memories")
    count: int = Field(..., description="Number of memories found")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Memories retrieved successfully",
                "memories": [
                    {
                        "id": "mem_123",
                        "text": "User loves playing chess on weekends",
                        "score": 0.95,
                        "metadata": {"timestamp": "2024-01-15T10:30:00"}
                    }
                ],
                "count": 1
            }
        }
    }


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    mem0: str = Field(..., description="mem0 connection status")
    timestamp: str = Field(..., description="Health check timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "memory-service",
                "mem0": "connected",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    }