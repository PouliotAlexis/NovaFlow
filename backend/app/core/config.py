"""
NovaFlow Backend Configuration
"""
from pydantic_settings import BaseSettings
from typing import Literal
import os
import platform

def get_app_data_dir() -> str:
    # Répertoire de stockage local de l'application selon l'OS
    if platform.system() == "Windows":
        base_dir = os.getenv("APPDATA") or os.path.expanduser("~")
    elif platform.system() == "Darwin":  # macOS
        base_dir = os.path.expanduser("~/Library/Application Support")
    else:  # Linux / autre
        base_dir = os.getenv("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    
    app_dir = os.path.join(base_dir, "NovaFlow")
    os.makedirs(app_dir, exist_ok=True)
    os.makedirs(os.path.join(app_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(app_dir, "chromadb_v2"), exist_ok=True)
    return app_dir

APP_DATA_DIR = get_app_data_dir()

class Settings(BaseSettings):
    """Configuration principale de NovaFlow."""
    
    # App
    APP_NAME: str = "NovaFlow"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # AI Engine
    AI_MODE: Literal["local", "cloud", "openai", "groq"] = "local"
    
    # Ollama (Local AI)
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    
    # Cloud AI — OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Cloud AI — Groq (API compatible OpenAI, gratuit)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{os.path.join(APP_DATA_DIR, 'novaflow.db')}"
    DATA_DIR: str = os.path.join(APP_DATA_DIR, "data")
    CHROMA_DIR: str = os.path.join(APP_DATA_DIR, "chromadb_v2")
    
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
    MOODLE_URL: str = "https://moodle.usherbrooke.ca/"
    CHROME_USER_DATA_DIR: str = os.path.expandvars("%LOCALAPPDATA%/Google/Chrome/User Data")
    MOODLE_SYNC_INTERVAL_HOURS: int = 4
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
