"""
NovaFlow - Service Task Manager (SQLAlchemy Version)

Manage storage and manipulation of tasks (Todo List) using SQLAlchemy and PostgreSQL/SQLite.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import Task as DBTask

class NovaFlowTask:
    """Modèle de données pour une tâche (conserve la compatibilité avec l'ancien code)."""
    def __init__(self, id: str, title: str, priority: str = "medium", meta: str = "NovaFlow", 
                 done: bool = False, parent_event_id: Optional[str] = None, created_at: Optional[str] = None,
                 external_id: Optional[str] = None, source: Optional[str] = "local", due_date: Optional[str] = None,
                 description: Optional[str] = "", course_id: Optional[str] = None):
        self.id = id
        self.title = title
        self.priority = priority
        self.meta = meta
        self.done = done
        self.parent_event_id = parent_event_id
        self.created_at = created_at
        self.external_id = external_id
        self.source = source
        self.due_date = due_date
        self.description = description or ""
        self.course_id = course_id

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
            "due_date": self.due_date,
            "description": self.description,
            "course_id": self.course_id
        }

    @classmethod
    def from_db(cls, db_task: DBTask) -> 'NovaFlowTask':
        return cls(
            id=db_task.id,
            title=db_task.title,
            priority=db_task.priority,
            meta=db_task.meta,
            done=db_task.done,
            parent_event_id=db_task.parent_event_id,
            created_at=db_task.created_at.isoformat() if db_task.created_at else None,
            external_id=db_task.external_id,
            source=db_task.source,
            due_date=db_task.due_date,
            description=db_task.description,
            course_id=db_task.course_id
        )

class TaskManager:
    _instance = None

    def __init__(self):
        # On ne garde plus de liste en mémoire, on interroge la DB
        pass

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload(self):
        """Inutile maintenant que la DB est la source de vérité directe."""
        pass

    def get_all_tasks(self, user_id: str = None) -> List[Dict[str, Any]]:
        with SessionLocal() as db:
            query = db.query(DBTask)
            if user_id:
                query = query.filter(DBTask.user_id == user_id)
            else:
                query = query.filter(DBTask.user_id == None)
            tasks = query.order_by(DBTask.created_at.desc()).all()
            return [NovaFlowTask.from_db(t).to_dict() for t in tasks]

    def get_task_object(self, task_id: str) -> Optional[NovaFlowTask]:
        with SessionLocal() as db:
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            return NovaFlowTask.from_db(db_task) if db_task else None

    def add_task(self, title: str, priority: str = "medium", meta: str = "NovaFlow", 
                 parent_event_id: Optional[str] = None, external_id: Optional[str] = None, 
                 source: Optional[str] = "local", due_date: Optional[str] = None,
                 course_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        with SessionLocal() as db:
            # Dédoublonnage
            if external_id:
                existing = db.query(DBTask).filter(DBTask.external_id == external_id, DBTask.source == source).first()
                if existing:
                    return NovaFlowTask.from_db(existing).to_dict()
            else:
                existing = db.query(DBTask).filter(
                    DBTask.title == title, 
                    DBTask.meta == meta, 
                    DBTask.parent_event_id == parent_event_id, 
                    DBTask.course_id == course_id,
                    DBTask.user_id == user_id,
                    DBTask.done == False
                ).first()
                if existing:
                    return NovaFlowTask.from_db(existing).to_dict()
            
            new_id = str(uuid.uuid4())
            db_task = DBTask(
                id=new_id,
                title=title,
                priority=priority,
                meta=meta,
                done=False,
                parent_event_id=parent_event_id,
                external_id=external_id,
                source=source,
                due_date=due_date,
                course_id=course_id,
                user_id=user_id,
                sync_status="local"
            )
            db.add(db_task)
            db.commit()
            db.refresh(db_task)
            return NovaFlowTask.from_db(db_task).to_dict()

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with SessionLocal() as db:
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if db_task:
                if "title" in updates: db_task.title = updates["title"]
                if "priority" in updates: db_task.priority = updates["priority"]
                if "meta" in updates: db_task.meta = updates["meta"]
                if "done" in updates: db_task.done = updates["done"]
                if "parent_event_id" in updates: db_task.parent_event_id = updates["parent_event_id"]
                if "external_id" in updates: db_task.external_id = updates["external_id"]
                if "source" in updates: db_task.source = updates["source"]
                if "due_date" in updates: db_task.due_date = updates["due_date"]
                if "description" in updates: db_task.description = updates["description"]
                if "course_id" in updates: db_task.course_id = updates["course_id"]
                
                db_task.sync_status = "pending" # Marquer pour sync cloud future
                
                db.commit()
                db.refresh(db_task)
                return NovaFlowTask.from_db(db_task).to_dict()
            return None

    def delete_task(self, task_id: str) -> bool:
        with SessionLocal() as db:
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if db_task:
                db.delete(db_task)
                db.commit()
                return True
            return False

    def delete_tasks_by_event(self, event_id: str) -> int:
        with SessionLocal() as db:
            count = db.query(DBTask).filter(DBTask.parent_event_id == event_id).delete()
            db.commit()
            return count

    def toggle_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as db:
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if db_task:
                db_task.done = not db_task.done
                db_task.sync_status = "pending"
                db.commit()
                db.refresh(db_task)
                return NovaFlowTask.from_db(db_task).to_dict()
            return None

    def link_task_to_event(self, task_id: str, event_id: str) -> Optional[Dict[str, Any]]:
        return self.update_task(task_id, {"parent_event_id": event_id})

# --- Module Wrapper Functions (for backward compatibility) ---

_manager = TaskManager.instance()

def get_tasks(user_id: str = None) -> List[Dict[str, Any]]:
    return _manager.get_all_tasks(user_id=user_id)

def add_task(title: str, priority: str = "medium", meta: str = "NovaFlow", parent_event_id: Optional[str] = None, due_date: Optional[str] = None, course_id: Optional[str] = None, user_id: str = None) -> Dict[str, Any]:
    return _manager.add_task(title, priority, meta, parent_event_id, due_date=due_date, course_id=course_id, user_id=user_id)

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
