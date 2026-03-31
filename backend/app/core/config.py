"""
NovaFlow Backend Configuration
"""
from pydantic_settings import BaseSettings


from typing import Literal
import os

# Calculate BASE_DIR (the 'backend' directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Settings(BaseSettings):
    """Configuration principale de NovaFlow."""
    
    # App
    APP_NAME: str = "NovaFlow"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Base URLs for Redirects (Local vs Production)
    # IMPORTANT: On Vercel/Render, set APP_BASE_URL to your public domain (e.g. https://nova-flow-mu.vercel.app)
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    
    # Paths
    BASE_DIR: str = os.getenv("BASE_DIR", BASE_DIR)
    # Default credentials dir: can be overridden via env var
    CREDENTIALS_DIR: str = os.getenv("CREDENTIALS_DIR", os.path.join(BASE_DIR, "credentials"))
    
    # AI Engine
    AI_MODE: Literal["local", "openai", "groq"] = "local"
    
    # Ollama (Local AI)
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    
    # Cloud AI (OpenAI)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Browserless
    BROWSERLESS_API_KEY: str = ""
    BROWSERLESS_URL: str = ""  # Optionnel: ws://localhost:3000 ou wss://...
    
    # Database
    DATABASE_URL: str = "sqlite:///./novaflow.db"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # Google Calendar OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # Alternative to file: the entire JSON content of the client secret file
    GOOGLE_CLIENT_SECRET_JSON: str = ""
    # Google uses the APP_BASE_URL if GOOGLE_REDIRECT_URI is not explicitly set
    GOOGLE_REDIRECT_URI: str = "" 
    
    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"
    # Microsoft uses the APP_BASE_URL if MICROSOFT_REDIRECT_URI is not explicitly set
    MICROSOFT_REDIRECT_URI: str = ""
    
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

# Diagnostic prints for startup (helpful in production logs like Render/Vercel)
if settings.DEBUG:
    print(f"DEBUG: BASE_DIR: {settings.BASE_DIR}")
    print(f"DEBUG: CREDENTIALS_DIR: {settings.CREDENTIALS_DIR}")
    print(f"DEBUG: APP_BASE_URL: {settings.APP_BASE_URL}")
