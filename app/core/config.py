try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./simco.db"
    
    # LLM Configuration
    LLM_PROVIDER: str = "ollama"
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "mistral"
    
    # External APIs (backup)
    OPENAI_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    
    # Computer Vision
    OPENFACE_BIN: Optional[str] = None
    MEDIAPIPE_ENABLED: bool = True
    
    # ML Models
    MODEL_PATH: str = "./models"
    CONFIDENCE_THRESHOLD: float = 0.7
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    REPORTS_DIR: str = "./reports"
    
    # Email / SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()
