"""
NovaFlow - Service Notification Manager (OOP Version)
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional

# Chemin vers le fichier de stockage
from app.core.config import settings
NOTIFICATIONS_FILE = os.path.join(settings.DATA_DIR, "notifications.json")

class Notification:
    def __init__(self, id: str, title: str, content: str, type: str, timestamp: str, read: bool = False):
        self.id = id
        self.title = title
        self.content = content
        self.type = type
        self.timestamp = timestamp
        self.read = read

    def mark_read(self):
        self.read = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "type": self.type,
            "timestamp": self.timestamp,
            "read": self.read
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Notification':
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            type=data["type"],
            timestamp=data["timestamp"],
            read=data.get("read", False)
        )

class NotificationManager:
    _instance = None

    def __init__(self):
        self._notifications: List[Notification] = []
        self._load_notifications()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_notifications(self):
        if not os.path.exists(NOTIFICATIONS_FILE):
            self._notifications = []
            return
        try:
            with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._notifications = [Notification.from_dict(n) for n in data]
        except Exception as e:
            print(f"Erreur chargement notifications: {e}")
            self._notifications = []

    def reload(self):
        """Recharge les données depuis le disque (utile après un reset)."""
        self._load_notifications()

    def _save_notifications(self):
        os.makedirs(os.path.dirname(NOTIFICATIONS_FILE), exist_ok=True)
        data = [n.to_dict() for n in self._notifications]
        try:
            with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde notifications: {e}")

    def add_notification(self, title: str, content: str, type: str = "info") -> Dict:
        new_notif = Notification(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            type=type,
            timestamp=datetime.now().isoformat(),
            read=False
        )
        self._notifications.insert(0, new_notif)
        self._notifications = self._notifications[:50] # Keep last 50
        self._save_notifications()
        return new_notif.to_dict()

    def get_notifications(self, unread_only: bool = False) -> List[Dict]:
        if unread_only:
            return [n.to_dict() for n in self._notifications if not n.read]
        return [n.to_dict() for n in self._notifications]

    def mark_as_read(self, notif_id: str) -> bool:
        for n in self._notifications:
            if n.id == notif_id:
                n.mark_read()
                self._save_notifications()
                return True
        return False

    def mark_all_as_read(self) -> int:
        count = 0
        for n in self._notifications:
            if not n.read:
                n.mark_read()
                count += 1
        if count > 0:
            self._save_notifications()
        return count

    def delete_notification(self, notif_id: str) -> bool:
        initial_len = len(self._notifications)
        self._notifications = [n for n in self._notifications if n.id != notif_id]
        if len(self._notifications) < initial_len:
            self._save_notifications()
            return True
        return False

    def clear_all_notifications(self):
        self._notifications = []
        self._save_notifications()

# --- Wrapper functions ---

_manager = NotificationManager.instance()

def add_notification(title: str, content: str, type: str = "info") -> Dict:
    return _manager.add_notification(title, content, type)

def get_notifications(unread_only: bool = False) -> List[Dict]:
    return _manager.get_notifications(unread_only)

def mark_as_read(notif_id: str) -> bool:
    return _manager.mark_as_read(notif_id)

def mark_all_as_read() -> int:
    return _manager.mark_all_as_read()

def delete_notification(notif_id: str) -> bool:
    return _manager.delete_notification(notif_id)

def clear_all_notifications():
    _manager.clear_all_notifications()
