from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AI Evaluation System"
    opencompass_path: str = "../../libs/OpenCompass"
    redis_url: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"

settings = Settings() 