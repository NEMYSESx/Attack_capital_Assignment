from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str
    
    GROQ_API_KEY: str
    LLM_MODEL: str = "llama-3-70b-8192"
    
    MEMORY_SERVICE_URL: str = "http://localhost:8001"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    ENVIRONMENT: str = "development"
    
    AGENT_NAME: str = "AI Assistant"
    MAX_CONTEXT_LENGTH: int = 4000
    TEMPERATURE: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()