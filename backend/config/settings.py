"""
Configuration settings for the SIMCO backend application.
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SIMCO - Cognitive Evaluation System"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]
    
    # Ollama LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"
    OLLAMA_TIMEOUT: int = 120
    
    # ML Models
    ML_MODELS_PATH: str = "data/models"
    USE_ML_MODELS: bool = True
    
    # Data Collection
    TRAINING_DATA_PATH: str = "data/training"
    AUTO_COLLECT_DATA: bool = True
    
    # Session Management
    SESSION_TIMEOUT: int = 3600  # 1 hour in seconds
    
    # Quiz Settings
    DEFAULT_QUIZ_LENGTH: int = 10
    DEFAULT_TIME_LIMIT: int = 1200  # 20 minutes in seconds
    
    # Behavioral Analysis
    WEBCAM_ENABLED: bool = True
    BLINK_RATE_THRESHOLD: float = 30.0
    HEAD_MOVEMENT_THRESHOLD: float = 5.0
    GAZE_STABILITY_THRESHOLD: float = 0.6
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
