from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional


class MemoryStoreRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username to associate memory with")
    message: str = Field(..., min_length=1, description="User message to store")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "john_doe",
                "message": "I love playing chess on weekends",
                "metadata": {"session_id": "chat_123", "timestamp": "2024-01-15T10:30:00"}
            }
        }
    }


class MemoryRetrieveRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username to retrieve memories for")
    query: str = Field(..., min_length=1, description="Query to search memories")
    limit: Optional[int] = Field(default=5, ge=1, le=20, description="Maximum number of memories to retrieve")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "john_doe",
                "query": "What are my hobbies?",
                "limit": 5
            }
        }
    }