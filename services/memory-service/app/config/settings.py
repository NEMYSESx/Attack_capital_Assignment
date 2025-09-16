from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, List


class Settings(BaseSettings):
    SERVICE_NAME: str = "memory-service"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    MEM0_API_KEY: Optional[str] = Field(None, description="Mem0 API key for hosted version")
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    CORS_ORIGINS: List[str] = ["*"]
    
    ALLOWED_HOSTS: List[str] = ["*"]
    
    RATE_LIMIT: str = "100/minute"
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v_upper
    
    @field_validator("MEM0_API_KEY")
    @classmethod
    def validate_mem0_api_key(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            raise ValueError("MEM0_API_KEY is required for hosted mem0 service")
        return v.strip()

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings