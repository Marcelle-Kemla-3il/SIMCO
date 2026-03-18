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
    OLLAMA_TIMEOUT_SECONDS: float = 20.0
    
    # External APIs
    OPENAI_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_API_URL: str = "https://api.mistral.ai"
    MISTRAL_MODEL: str = "mistral-small-latest"
    
    # Computer Vision
    MEDIAPIPE_ENABLED: bool = True
    
    # File Storage
    MODEL_PATH: Optional[str] = None
    UPLOAD_DIR: Optional[str] = None
    REPORTS_DIR: Optional[str] = None
    
    # Email Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: Optional[bool] = None
    EMAIL_FROM: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: Optional[str] = None

    # CV microservice
    CV_SERVICE_URL: Optional[str] = None

    # Admin (Basic Auth)
    ADMIN_USERNAME: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "allow"  # Permettre les champs supplémentaires

settings = Settings()
