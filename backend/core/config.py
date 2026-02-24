"""
NovaFlow Backend Configuration
"""
from pydantic_settings import BaseSettings


from typing import Literal
import os

class Settings(BaseSettings):
    """Configuration principale de NovaFlow."""
    
    # App
    APP_NAME: str = "NovaFlow"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # AI Engine
    AI_MODE: Literal["local", "cloud"] = "local"
    
    # Ollama (Local AI)
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    
    # Cloud AI (Fallback)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Database
    DATABASE_URL: str = "sqlite:///./novaflow.db"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # Google Calendar OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    
    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/api/auth/microsoft/callback"
    
    # Moodle Downloads
    MOODLE_DOWNLOADS_DESTINATION: str = os.path.expanduser("~/Documents/NovaFlow_Courses")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
