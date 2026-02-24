"""
NovaFlow - Service Event Manager (OOP Version)

Manages NovaFlow events (Source of Truth) using Object-Oriented Principles.
A NovaFlowEvent is a persistent object linking an external event (Google, Outlook, etc.)
to its internal child tasks.
"""

import json
import os
import uuid
import datetime
from typing import List, Dict, Optional, Any

from services.task_manager import TaskManager


# Chemin du fichier de données
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")

def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

class NovaFlowEvent:
    def __init__(self, id: str, external_id: str, source: str, title: str, 
                 start: str, updated: str, desc_hash: str, task_ids: List[str] = None, created_at: str = None):
        self.id = id
        self.external_id = external_id
        self.source = source
        self.title = title
        self.start = start
        self.updated = updated
        self.desc_hash = desc_hash
        self.task_ids = task_ids or []
        self.created_at = created_at or datetime.datetime.now().isoformat()

    def add_task(self, task_id: str):
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)

    def remove_task(self, task_id: str):
        if task_id in self.task_ids:
            self.task_ids.remove(task_id)

    def clear_tasks(self) -> int:
        """Removes and deletes all child tasks."""
        count = 0
        tm = TaskManager.instance()
        for tid in list(self.task_ids): # Copy list to iterate safely
            if tm.delete_task(tid):
                count += 1
        self.task_ids = []
        return count

    def update(self, updates: Dict[str, Any]):
        if "title" in updates: self.title = updates["title"]
        if "updated" in updates: self.updated = updates["updated"]
        if "start" in updates: self.start = updates["start"]
        if "desc_hash" in updates: self.desc_hash = updates["desc_hash"]
        # task_ids managed separately via add/remove methods usually, but can be set here if needed
        if "task_ids" in updates: self.task_ids = updates["task_ids"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "external_id": self.external_id,
            "source": self.source,
            "title": self.title,
            "start": self.start,
            "updated": self.updated,
            "desc_hash": self.desc_hash,
            "task_ids": self.task_ids,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NovaFlowEvent':
        return cls(
            id=data["id"],
            external_id=data["external_id"],
            source=data["source"],
            title=data["title"],
            start=data["start"],
            updated=data["updated"],
            desc_hash=data["desc_hash"],
            task_ids=data.get("task_ids", []),
            created_at=data.get("created_at")
        )

class EventManager:
    _instance = None

    def __init__(self):
        self._events: Dict[str, NovaFlowEvent] = {}
        self._load_events()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_events(self):
        if not os.path.exists(EVENTS_FILE):
             self._events = {}
             return
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # data is dict id -> event_dict
                self._events = {eid: NovaFlowEvent.from_dict(edata) for eid, edata in data.items()}
        except (json.JSONDecodeError, FileNotFoundError):
            self._events = {}

    def reload(self):
        """Recharge les données depuis le disque (utile après un reset)."""
        self._load_events()

    def _save_events(self):
        _ensure_data_dir()
        data = {eid: evt.to_dict() for eid, evt in self._events.items()}
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_events(self) -> List[NovaFlowEvent]:
        return list(self._events.values())

    def get_event(self, event_id: str) -> Optional[NovaFlowEvent]:
        return self._events.get(event_id)

    def get_event_by_external_id(self, external_id: str, source: str) -> Optional[NovaFlowEvent]:
        for evt in self._events.values():
            if evt.external_id == external_id and evt.source == source:
                return evt
        return None

    def create_event(self, external_id: str, source: str, title: str, start: str, updated: str, desc_hash: str) -> NovaFlowEvent:
        existing = self.get_event_by_external_id(external_id, source)
        if existing:
            return existing

        new_id = str(uuid.uuid4())
        new_event = NovaFlowEvent(new_id, external_id, source, title, start, updated, desc_hash)
        self._events[new_id] = new_event
        self._save_events()
        return new_event

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> Optional[NovaFlowEvent]:
        evt = self.get_event(event_id)
        if evt:
            evt.update(updates)
            self._save_events()
            return evt
        return None

    def delete_event(self, event_id: str) -> bool:
        evt = self.get_event(event_id)
        if not evt:
            print(f"DEBUG: Delete failed - Event {event_id} not found")
            return False
        
        count_deleted = evt.clear_tasks()
        print(f"🗑️ Event {evt.title} supprimé avec {count_deleted} tâches enfants. (Internal ID: {event_id})")
        
        del self._events[event_id]
        self._save_events()
        print(f"DEBUG: Event deleted and saved.")
        return True

    def add_task_to_event(self, event_id: str, task_id: str) -> bool:
        evt = self.get_event(event_id)
        if evt:
            evt.add_task(task_id)
            self._save_events()
            return True
        return False
    
    def remove_task_from_event(self, event_id: str, task_id: str) -> bool:
        evt = self.get_event(event_id)
        if evt:
            evt.remove_task(task_id)
            self._save_events()
            return True
        return False

    def clear_event_tasks(self, event_id: str) -> int:
        evt = self.get_event(event_id)
        if evt:
            count = evt.clear_tasks()
            self._save_events()
            return count
        return 0

# --- Module Wrapper Functions ---

_manager = EventManager.instance()

def get_all_events() -> List[Dict[str, Any]]:
    return [e.to_dict() for e in _manager.get_all_events()]

def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    evt = _manager.get_event(event_id)
    return evt.to_dict() if evt else None

def get_event_by_external_id(external_id: str, source: str) -> Optional[Dict[str, Any]]:
    evt = _manager.get_event_by_external_id(external_id, source)
    return evt.to_dict() if evt else None

def create_event(external_id: str, source: str, title: str, start: str, updated: str, desc_hash: str) -> Dict[str, Any]:
    return _manager.create_event(external_id, source, title, start, updated, desc_hash).to_dict()

def update_event(event_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    evt = _manager.update_event(event_id, updates)
    return evt.to_dict() if evt else None

def delete_event(event_id: str) -> bool:
    return _manager.delete_event(event_id)

def add_task_to_event(event_id: str, task_id: str) -> bool:
    return _manager.add_task_to_event(event_id, task_id)

def remove_task_from_event(event_id: str, task_id: str) -> bool:
    return _manager.remove_task_from_event(event_id, task_id)

def clear_event_tasks(event_id: str) -> int:
    return _manager.clear_event_tasks(event_id)
