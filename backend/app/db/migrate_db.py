import json
import os
import sys
from datetime import datetime

# Ajouter le chemin du backend pour l'import local
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.database import engine, SessionLocal, Base
from app.db.models import Task, Event, ChatMessage, MoodleExtCourse
from sqlalchemy.orm import Session

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def migrate():
    print("🚀 Début de la migration NovaFlow (JSON -> SQL)...")
    
    # 1. Créer les tables si elles n'existent pas
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées ou déjà présentes.")
    
    db: Session = SessionLocal()
    
    try:
        # 2. Migration des ÉVÉNEMENTS
        events_file = os.path.join(DATA_DIR, "events.json")
        if os.path.exists(events_file):
            print("📅 Migration des événements...")
            with open(events_file, "r", encoding="utf-8") as f:
                events_data = json.load(f)
                count = 0
                for eid, edata in events_data.items():
                    # Vérifier si déjà présent
                    existing = db.query(Event).filter(Event.id == eid).first()
                    if not existing:
                        db.add(Event(
                            id=eid,
                            external_id=edata.get("external_id"),
                            source=edata.get("source", "local"),
                            title=edata.get("title", "Sans titre"),
                            start=edata.get("start"),
                            updated=edata.get("updated"),
                            desc_hash=edata.get("desc_hash"),
                            category=edata.get("category"),
                            created_at=datetime.fromisoformat(edata["created_at"]) if edata.get("created_at") else None
                        ))
                        count += 1
                print(f"   Done: {count} événements migrés.")

        # 3. Migration des TÂCHES
        tasks_file = os.path.join(DATA_DIR, "tasks.json")
        if os.path.exists(tasks_file):
            print("📝 Migration des tâches...")
            with open(tasks_file, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)
                count = 0
                for tdata in tasks_data:
                    tid = tdata["id"]
                    existing = db.query(Task).filter(Task.id == tid).first()
                    if not existing:
                        db.add(Task(
                            id=tid,
                            title=tdata.get("title"),
                            priority=tdata.get("priority", "medium"),
                            meta=tdata.get("meta", "NovaFlow"),
                            done=tdata.get("done", False),
                            due_date=tdata.get("due_date"),
                            description=tdata.get("description", ""),
                            course_id=tdata.get("course_id"),
                            parent_event_id=tdata.get("parent_event_id"),
                            external_id=tdata.get("external_id"),
                            source=tdata.get("source", "local"),
                            sync_status="local",
                            created_at=datetime.fromisoformat(tdata["created_at"]) if tdata.get("created_at") else None
                        ))
                        count += 1
                print(f"   Done: {count} tâches migrées.")

        # 4. Migration de l'HISTORIQUE DE CHAT
        chat_file = os.path.join(DATA_DIR, "chat_history.json")
        if os.path.exists(chat_file):
            print("💬 Migration de l'historique de chat...")
            with open(chat_file, "r", encoding="utf-8") as f:
                chat_data = json.load(f)
                count = 0
                for cdata in chat_data:
                    cid = cdata["id"]
                    existing = db.query(ChatMessage).filter(ChatMessage.id == cid).first()
                    if not existing:
                        # Parsing timestamp
                        ts = None
                        if cdata.get("timestamp"):
                            try:
                                ts = datetime.fromisoformat(cdata["timestamp"])
                            except: pass
                            
                        db.add(ChatMessage(
                            id=cid,
                            role=cdata.get("role"),
                            content=cdata.get("content"),
                            timestamp=ts
                        ))
                        count += 1
                print(f"   Done: {count} messages migrés.")

        # 5. Migration des COURS MOODLE (Extension)
        moodle_courses_file = os.path.join(DATA_DIR, "moodle_ext_courses.json")
        if os.path.exists(moodle_courses_file):
            print("🎓 Migration des cours Moodle...")
            with open(moodle_courses_file, "r", encoding="utf-8") as f:
                courses_data = json.load(f)
                count = 0
                for cdata in courses_data:
                    cid = str(cdata.get("id"))
                    existing = db.query(MoodleExtCourse).filter(MoodleExtCourse.id == cid).first()
                    if not existing:
                        db.add(MoodleExtCourse(
                            id=cid,
                            fullname=cdata.get("fullname"),
                            shortname=cdata.get("shortname")
                        ))
                        count += 1
                print(f"   Done: {count} cours Moodle migrés.")

        # 6. Migration des FICHIEURS MOODLE SYNC
        moodle_files_file = os.path.join(DATA_DIR, "moodle_ext_downloaded_keys.json")
        if os.path.exists(moodle_files_file):
            print("📁 Migration des clés de fichiers Moodle...")
            with open(moodle_files_file, "r", encoding="utf-8") as f:
                keys_data = json.load(f)
                count = 0
                from app.db.models import MoodleSyncedFile
                for fkey in keys_data:
                    existing = db.query(MoodleSyncedFile).filter(MoodleSyncedFile.file_key == fkey).first()
                    if not existing:
                        db.add(MoodleSyncedFile(file_key=fkey))
                        count += 1
                print(f"   Done: {count} clés de fichiers migrées.")

        db.commit()
        print("\n✨ Migration terminée avec succès !")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Erreur lors de la migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
