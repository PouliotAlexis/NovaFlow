"""
NovaFlow - Service Event Manager (SQLAlchemy Version)

Manages NovaFlow events using SQLAlchemy and PostgreSQL/SQLite.
A Event in DB links to its internal child tasks via the Task.parent_event_id relation.
"""

import uuid
import datetime
import os
import json
from typing import List, Dict, Optional, Any
from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Event as DBEvent, Task as DBTask, MoodleExtCourse as DBMoodleCourse
from sqlalchemy.orm import Session

class NovaFlowEvent:
    def __init__(self, id: str, external_id: str, source: str, title: str, 
                 start: str, updated: str, desc_hash: str, task_ids: List[str] = None, 
                 created_at: str = None, category: str = None):
        self.id = id
        self.external_id = external_id
        self.source = source
        self.title = title
        self.start = start
        self.updated = updated
        self.desc_hash = desc_hash
        self.task_ids = task_ids or []
        self.created_at = created_at
        self.category = category

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
            "created_at": self.created_at,
            "category": self.category
        }

    @classmethod
    def from_db(cls, db_event: DBEvent) -> 'NovaFlowEvent':
        # On récupère les IDs des tâches associées
        tids = [t.id for t in db_event.tasks]
        return cls(
            id=db_event.id,
            external_id=db_event.external_id,
            source=db_event.source,
            title=db_event.title,
            start=db_event.start,
            updated=db_event.updated,
            desc_hash=db_event.desc_hash,
            task_ids=tids,
            created_at=db_event.created_at.isoformat() if db_event.created_at else None,
            category=db_event.category
        )

class EventManager:
    _instance = None

    def __init__(self):
        pass

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload(self):
        pass

    def get_all_events(self, user_id: str = None) -> List[NovaFlowEvent]:
        with SessionLocal() as db:
            query = db.query(DBEvent)
            if user_id:
                query = query.filter(DBEvent.user_id == user_id)
            else:
                query = query.filter(DBEvent.user_id == None)
            events = query.all()
            return [NovaFlowEvent.from_db(e) for e in events]

    def get_event(self, event_id: str) -> Optional[NovaFlowEvent]:
        with SessionLocal() as db:
            db_event = db.query(DBEvent).filter(DBEvent.id == event_id).first()
            return NovaFlowEvent.from_db(db_event) if db_event else None

    def get_event_by_external_id(self, external_id: str, source: str) -> Optional[NovaFlowEvent]:
        with SessionLocal() as db:
            db_event = db.query(DBEvent).filter(DBEvent.external_id == external_id, DBEvent.source == source).first()
            return NovaFlowEvent.from_db(db_event) if db_event else None

    def create_event(self, external_id: str, source: str, title: str, start: str, updated: str, desc_hash: str, user_id: str = None) -> NovaFlowEvent:
        with SessionLocal() as db:
            existing = db.query(DBEvent).filter(DBEvent.external_id == external_id, DBEvent.source == source).first()
            if existing:
                return NovaFlowEvent.from_db(existing)

            new_id = str(uuid.uuid4())
            db_event = DBEvent(
                id=new_id,
                external_id=external_id,
                source=source,
                title=title,
                start=start,
                updated=updated,
                desc_hash=desc_hash,
                user_id=user_id
            )
            db.add(db_event)
            db.commit()
            db.refresh(db_event)
            return NovaFlowEvent.from_db(db_event)

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> Optional[NovaFlowEvent]:
        with SessionLocal() as db:
            db_event = db.query(DBEvent).filter(DBEvent.id == event_id).first()
            if db_event:
                if "title" in updates: db_event.title = updates["title"]
                if "updated" in updates: db_event.updated = updates["updated"]
                if "start" in updates: db_event.start = updates["start"]
                if "desc_hash" in updates: db_event.desc_hash = updates["desc_hash"]
                if "category" in updates: db_event.category = updates["category"]
                
                db.commit()
                db.refresh(db_event)
                return NovaFlowEvent.from_db(db_event)
            return None

    def delete_event(self, event_id: str) -> bool:
        with SessionLocal() as db:
            db_event = db.query(DBEvent).filter(DBEvent.id == event_id).first()
            if not db_event:
                return False
            
            # Supprimer les tâches d'abord (ou laisser cascade si configuré)
            # Ici on le fait explicitement par sécurité
            db.query(DBTask).filter(DBTask.parent_event_id == event_id).delete()
            
            db.delete(db_event)
            db.commit()
            return True

    def add_task_to_event(self, event_id: str, task_id: str) -> bool:
        with SessionLocal() as db:
            db_task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if db_task:
                db_task.parent_event_id = event_id
                db.commit()
                return True
            return False
    
    def remove_task_from_event(self, event_id: str, task_id: str) -> bool:
        with SessionLocal() as db:
            db_task = db.query(DBTask).filter(DBTask.id == task_id, DBTask.parent_event_id == event_id).first()
            if db_task:
                db_task.parent_event_id = None
                db.commit()
                return True
            return False

    def clear_event_tasks(self, event_id: str) -> int:
        with SessionLocal() as db:
            count = db.query(DBTask).filter(DBTask.parent_event_id == event_id).delete()
            db.commit()
            return count

    def find_course_id_by_text(self, text: str) -> Optional[str]:
        if not text:
            return None
        
        import re
        code_match = re.search(r'([A-Za-z]{3,4}-?\d{3,4})', text)
        target_code = code_match.group(1).upper() if code_match else None
        
        # Charger les cours depuis la DB (migrés depuis JSON précédemment)
        with SessionLocal() as db:
            all_courses = db.query(DBMoodleCourse).all()
            
            # 1. Match via code
            if target_code:
                for c in all_courses:
                    short = (c.shortname or "").upper()
                    full = (c.fullname or "").upper()
                    if target_code in short or target_code in full:
                        return c.id

            # 2. Match via mots-clés
            text_upper = text.upper()
            for c in all_courses:
                full = (c.fullname or "").upper()
                if not full or len(full) < 3: continue
                words = [w for w in full.split() if len(w) >= 4]
                for word in words:
                    if word in text_upper:
                        return c.id
                if full in text_upper:
                    return c.id
            
        return None

    def get_or_create_course_event(self, course_id: str) -> Optional[str]:
        if not course_id:
            return None
        
        ext_id = f"moodle_course_{course_id}"
        existing = self.get_event_by_external_id(ext_id, "moodle_ai") or self.get_event_by_external_id(ext_id, "moodle")
        if existing:
            return existing.id
        
        # Tenter de trouver le nom
        course_name = f"Cours {course_id}"
        with SessionLocal() as db:
            c = db.query(DBMoodleCourse).filter(DBMoodleCourse.id == course_id).first()
            if c:
                course_name = c.fullname

        now_iso = datetime.datetime.now().isoformat()
        new_event = self.create_event(
            external_id=ext_id,
            source="moodle_ai",
            title=course_name,
            start=now_iso,
            updated=now_iso,
            desc_hash="ai_pivot_event"
        )
        self.update_event(new_event.id, {"category": course_name})
        return new_event.id

# --- Module Wrapper Functions ---

_manager = EventManager.instance()

def get_all_events(user_id: str = None) -> List[Dict[str, Any]]:
    return [e.to_dict() for e in _manager.get_all_events(user_id=user_id)]

def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    evt = _manager.get_event(event_id)
    return evt.to_dict() if evt else None

def get_event_by_external_id(external_id: str, source: str) -> Optional[Dict[str, Any]]:
    evt = _manager.get_event_by_external_id(external_id, source)
    return evt.to_dict() if evt else None

def create_event(external_id: str, source: str, title: str, start: str, updated: str, desc_hash: str, user_id: str = None) -> Dict[str, Any]:
    return _manager.create_event(external_id, source, title, start, updated, desc_hash, user_id=user_id).to_dict()

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

def get_or_create_course_event(course_id: str) -> Optional[str]:
    return _manager.get_or_create_course_event(course_id)

def find_course_id_by_text(text: str) -> Optional[str]:
    return _manager.find_course_id_by_text(text)
