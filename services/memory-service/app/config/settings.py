from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MEM0_API_KEY: str
    MEM0_BASE_URL: str = "https://a"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()