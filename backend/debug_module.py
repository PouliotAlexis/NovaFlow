import os
import sys
import inspect
from pathlib import Path

# Ajouter le chemin du backend
sys.path.append(os.getcwd())

try:
    from app.services.calendar_sync.google import get_auth_url
    import app.services.calendar_sync.google as google_module
    
    print(f"Module file: {google_module.__file__}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Check source code of get_auth_url
    source = inspect.getsource(get_auth_url)
    print("--- Source of get_auth_url ---")
    print(source)
    print("------------------------------")
    
    # Check CREDENTIALS_DIR in that module
    print(f"CREDENTIALS_DIR in module: {getattr(google_module, 'CREDENTIALS_DIR', 'Not defined')}")

except Exception as e:
    print(f"Error: {e}")
