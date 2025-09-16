from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    
    MEM0_API_KEY: Optional[str] = None 
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = "../../.env"  


settings = Settings()