"""
NovaFlow - Service Task Manager (OOP Version)

manage storage and manipulation of tasks (Todo List) using Object-Oriented Principles.
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

# Chemin du fichier de données
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")

def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

class NovaFlowTask:
    def __init__(self, id: str, title: str, priority: str = "medium", meta: str = "NovaFlow", 
                 done: bool = False, parent_event_id: Optional[str] = None, created_at: Optional[str] = None,
                 external_id: Optional[str] = None, source: Optional[str] = "local", due_date: Optional[str] = None):
        self.id = id
        self.title = title
        self.priority = priority
        self.meta = meta
        self.done = done
        self.parent_event_id = parent_event_id
        self.created_at = created_at or datetime.now().isoformat()
        self.external_id = external_id
        self.source = source
        self.due_date = due_date

    def mark_done(self):
        self.done = True

    def mark_undone(self):
        self.done = False

    def toggle_status(self):
        self.done = not self.done

    def update(self, updates: Dict[str, Any]):
        if "title" in updates: self.title = updates["title"]
        if "priority" in updates: self.priority = updates["priority"]
        if "meta" in updates: self.meta = updates["meta"]
        if "done" in updates: self.done = updates["done"]
        if "parent_event_id" in updates: self.parent_event_id = updates["parent_event_id"]
        if "external_id" in updates: self.external_id = updates["external_id"]
        if "source" in updates: self.source = updates["source"]
        if "due_date" in updates: self.due_date = updates["due_date"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "meta": self.meta,
            "done": self.done,
            "parent_event_id": self.parent_event_id,
            "created_at": self.created_at,
            "external_id": self.external_id,
            "source": self.source,
            "due_date": self.due_date
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NovaFlowTask':
        return cls(
            id=data["id"],
            title=data["title"],
            priority=data.get("priority", "medium"),
            meta=data.get("meta", "NovaFlow"),
            done=data.get("done", False),
            parent_event_id=data.get("parent_event_id"),
            created_at=data.get("created_at"),
            external_id=data.get("external_id"),
            source=data.get("source", "local"),
            due_date=data.get("due_date")
        )

class TaskManager:
    _instance = None

    def __init__(self):
        self._tasks: List[NovaFlowTask] = []
        self._load_tasks()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_tasks(self):
        if not os.path.exists(TASKS_FILE):
            self._tasks = []
            return
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._tasks = [NovaFlowTask.from_dict(t) for t in data]
        except (json.JSONDecodeError, FileNotFoundError):
            self._tasks = []

    def reload(self):
        """Recharge les données depuis le disque (utile après un reset)."""
        self._load_tasks()

    def _save_tasks(self):
        _ensure_data_dir()
        data = [t.to_dict() for t in self._tasks]
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tasks]

    def get_task_object(self, task_id: str) -> Optional[NovaFlowTask]:
        return next((t for t in self._tasks if t.id == task_id), None)

    def add_task(self, title: str, priority: str = "medium", meta: str = "NovaFlow", 
                 parent_event_id: Optional[str] = None, external_id: Optional[str] = None, 
                 source: Optional[str] = "local", due_date: Optional[str] = None) -> Dict[str, Any]:
        # Dedup check
        for t in self._tasks:
            # Si on a un external_id, c'est le facteur de dédoublonnage principal
            if external_id and t.external_id == external_id and t.source == source:
                 return t.to_dict()
            
            # Sinon dédoublonnage classique (legacy)
            if not external_id and t.title == title and t.meta == meta and t.parent_event_id == parent_event_id and not t.done:
                return t.to_dict()
        
        new_task = NovaFlowTask(str(uuid.uuid4()), title, priority, meta, False, parent_event_id, 
                                external_id=external_id, source=source, due_date=due_date)
        self._tasks.insert(0, new_task)
        self._save_tasks()
        return new_task.to_dict()

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        task = self.get_task_object(task_id)
        if task:
            task.update(updates)
            self._save_tasks()
            return task.to_dict()
        return None

    def delete_task(self, task_id: str) -> bool:
        initial_len = len(self._tasks)
        self._tasks = [t for t in self._tasks if t.id != task_id]
        if len(self._tasks) < initial_len:
            self._save_tasks()
            return True
        return False

    def delete_tasks_by_event(self, event_id: str) -> int:
        initial_len = len(self._tasks)
        self._tasks = [t for t in self._tasks if t.parent_event_id != event_id]
        count = initial_len - len(self._tasks)
        if count > 0:
            self._save_tasks()
        return count

    def toggle_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.get_task_object(task_id)
        if task:
            task.toggle_status()
            self._save_tasks()
            return task.to_dict()
        return None

    def link_task_to_event(self, task_id: str, event_id: str) -> Optional[Dict[str, Any]]:
        return self.update_task(task_id, {"parent_event_id": event_id})

# --- Module Wrapper Functions (for backward compatibility) ---

_manager = TaskManager.instance()

def get_tasks() -> List[Dict[str, Any]]:
    return _manager.get_all_tasks()

def add_task(title: str, priority: str = "medium", meta: str = "NovaFlow", parent_event_id: Optional[str] = None, due_date: Optional[str] = None) -> Dict[str, Any]:
    return _manager.add_task(title, priority, meta, parent_event_id, due_date=due_date)

def update_task(task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _manager.update_task(task_id, updates)

def delete_task(task_id: str) -> bool:
    return _manager.delete_task(task_id)

def delete_tasks_by_event(event_id: str) -> int:
    return _manager.delete_tasks_by_event(event_id)

def toggle_task(task_id: str) -> Optional[Dict[str, Any]]:
    return _manager.toggle_task(task_id)

def link_task_to_event(task_id: str, event_id: str) -> Optional[Dict[str, Any]]:
    return _manager.link_task_to_event(task_id, event_id)
