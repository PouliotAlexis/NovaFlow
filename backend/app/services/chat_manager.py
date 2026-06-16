import json
import os
from datetime import datetime
from typing import List, Dict

from app.core.config import settings

# Chemin vers le fichier de stockage
CHAT_HISTORY_FILE = os.path.join(settings.DATA_DIR, "chat_history.json")

def load_chat_history() -> List[Dict]:
    """Charge l'historique complet depuis le fichier JSON."""
    if not os.path.exists(CHAT_HISTORY_FILE):
        return []
    
    try:
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur chargement historique: {e}")
        return []

def save_chat_message(role: str, content: str):
    """Ajoute un message à l'historique et sauvegarde."""
    history = load_chat_history()
    
    new_message = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    
    history.append(new_message)
    
    # Limiter l'historique aux 50 derniers messages pour garder le fichier léger
    if len(history) > 50:
        history = history[-50:]
        
    try:
        os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde historique: {e}")

def clear_chat_history():
    """Efface l'historique complet."""
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            os.remove(CHAT_HISTORY_FILE)
        except Exception as e:
            print(f"Erreur suppression historique: {e}")
