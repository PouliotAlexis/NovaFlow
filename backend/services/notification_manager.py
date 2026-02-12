import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional

# Chemin vers le fichier de stockage
NOTIFICATIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "notifications.json"
)

def _load_notifications() -> List[Dict]:
    """Charge les notifications depuis le fichier JSON."""
    if not os.path.exists(NOTIFICATIONS_FILE):
        return []
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur chargement notifications: {e}")
        return []

def _save_notifications(notifications: List[Dict]):
    """Sauvegarde les notifications dans le fichier JSON."""
    os.makedirs(os.path.dirname(NOTIFICATIONS_FILE), exist_ok=True)
    try:
        with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(notifications, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde notifications: {e}")

def add_notification(title: str, content: str, type: str = "info") -> Dict:
    """
    Ajoute une nouvelle notification.
    Types valides : 'info', 'warning', 'deadline', 'success'.
    """
    notifications = _load_notifications()
    
    new_notif = {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,
        "type": type,
        "timestamp": datetime.now().isoformat(),
        "read": False
    }
    
    # Garder les 50 dernières notifications
    notifications.insert(0, new_notif)
    notifications = notifications[:50]
    
    _save_notifications(notifications)
    return new_notif

def get_notifications(unread_only: bool = False) -> List[Dict]:
    """Récupère la liste des notifications."""
    notifications = _load_notifications()
    if unread_only:
        return [n for n in notifications if not n["read"]]
    return notifications

def mark_as_read(notif_id: str) -> bool:
    """Marque une notification spécifique comme lue."""
    notifications = _load_notifications()
    found = False
    for n in notifications:
        if n["id"] == notif_id:
            n["read"] = True
            found = True
            break
    
    if found:
        _save_notifications(notifications)
    return found

def mark_all_as_read() -> int:
    """Marque toutes les notifications comme lues."""
    notifications = _load_notifications()
    count = 0
    for n in notifications:
        if not n["read"]:
            n["read"] = True
            count += 1
    
    if count > 0:
        _save_notifications(notifications)
    return count

def delete_notification(notif_id: str) -> bool:
    """Supprime une notification spécifique."""
    notifications = _load_notifications()
    initial_length = len(notifications)
    notifications = [n for n in notifications if n["id"] != notif_id]
    
    if len(notifications) < initial_length:
        _save_notifications(notifications)
        return True
    return False

def clear_all_notifications():
    """Supprime toutes les notifications."""
    _save_notifications([])
