import json
import os
import shutil
import threading
import time
from datetime import datetime
from typing import List, Dict, Any

from app.db.database import SessionLocal
from app.db.models import MoodleExtCourse as DBMoodleCourse, MoodleSyncedFile as DBMoodleFile
from app.services.event_manager import EventManager

def _load_ext_courses() -> List[Dict]:
    with SessionLocal() as db:
        courses = db.query(DBMoodleCourse).all()
        return [{"id": c.id, "fullname": c.fullname, "shortname": c.shortname} for c in courses]

def _save_ext_courses(courses: List[Dict]):
    with SessionLocal() as db:
        for cdata in courses:
            cid = str(cdata["id"])
            existing = db.query(DBMoodleCourse).filter(DBMoodleCourse.id == cid).first()
            if existing:
                existing.fullname = cdata.get("fullname", existing.fullname)
                existing.shortname = cdata.get("shortname", existing.shortname)
            else:
                db.add(DBMoodleCourse(
                    id=cid,
                    fullname=cdata.get("fullname"),
                    shortname=cdata.get("shortname")
                ))
        db.commit()

def _load_ext_downloaded_keys() -> List[str]:
    with SessionLocal() as db:
        files = db.query(DBMoodleFile).all()
        return [f.file_key for f in files]

def _save_ext_downloaded_keys(keys: List[str]):
    with SessionLocal() as db:
        for fkey in keys:
            existing = db.query(DBMoodleFile).filter(DBMoodleFile.file_key == fkey).first()
            if not existing:
                db.add(DBMoodleFile(file_key=fkey))
        db.commit()

def _scan_for_existing_moodle_files():
    """Scanne le dossier Téléchargements pour trouver des fichiers Moodle non encore traités."""
    downloads_dir = os.path.expanduser("~/Downloads")
    moodle_root = os.path.join(downloads_dir, "NovaFlow_Moodle")
    
    found_files = []
    if not os.path.exists(moodle_root):
        return found_files
        
    for root, dirs, files in os.walk(moodle_root):
        for file in files:
            if file.endswith(".crdownload"):
                continue
            full_path = os.path.join(root, file)
            # Obtenir le chemin relatif à Downloads (ex: NovaFlow_Moodle/Course/File.pdf)
            rel_path = os.path.relpath(full_path, downloads_dir).replace("\\", "/")
            found_files.append(rel_path)
    return found_files

def process_moodle_files(downloaded_files: list):
    """
    Checks if the files sent by the extension exist in the Downloads folder
    and moves them to the permanent NovaFlow_Courses directory.
    """
    downloads_dir = os.path.expanduser("~/Downloads")
    moodle_root = os.path.join(downloads_dir, "NovaFlow_Moodle")
    
    # 1. Vérification stricte : y a-t-il des téléchargements en cours (.crdownload) ?
    is_downloading = False
    if os.path.exists(moodle_root):
        for root, dirs, files in os.walk(moodle_root):
            for file in files:
                if file.endswith(".crdownload"):
                    is_downloading = True
                    break
            if is_downloading:
                break
                
    if is_downloading:
        print("⏳ Téléchargement Chrome encore en cours (.crdownload détecté). Mise en attente du traitement Moodle.")
        
        # Relance automatique en arrière-plan
        def retry_task():
            time.sleep(15)
            print("🔄 Relance automatique du traitement des fichiers Moodle...")
            process_moodle_files(downloaded_files)
            
        threading.Thread(target=retry_task, daemon=True).start()
        return 0

    # 2. Si aucun téléchargement en cours, on peut déplacer
    existing_files = _scan_for_existing_moodle_files()
    all_to_process = list(set(downloaded_files + existing_files))
    
    if not all_to_process:
        return 0
        
    from app.core.config import settings
    target_base = settings.MOODLE_DOWNLOADS_DESTINATION
    
    moved_count = 0
    files_to_sync = []
    
    for relative_path in all_to_process:
        if not relative_path.startswith("NovaFlow_Moodle"):
            continue
            
        source_path = os.path.join(downloads_dir, relative_path)
        
        if os.path.exists(source_path):
            clean_rel_path = relative_path.replace("NovaFlow_Moodle/", "", 1)
            target_path = os.path.join(target_base, clean_rel_path)
            
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            try:
                shutil.move(source_path, target_path)
                moved_count += 1
                files_to_sync.append((target_path, clean_rel_path))
                print(f"✅ Moved Moodle file: {target_path}")
            except Exception as e:
                print(f"❌ Failed to move Moodle file {source_path}: {e}")
                
    # Trigger Google Drive Sync
    if files_to_sync:
        try:
            from app.services.calendar_sync.google import upload_files_batch_to_drive
            threading.Thread(
                target=upload_files_batch_to_drive,
                args=(files_to_sync,),
                daemon=True
            ).start()
        except Exception as e:
            print(f"⚠️ Failed to start Drive Batch Sync thread: {e}")

    return moved_count

def process_extension_payload(payload: dict) -> dict:
    # 1. Courses
    courses = payload.get("courses", [])
    if courses:
        _save_ext_courses(courses)
        
    # 2. Files
    downloaded_files = payload.get("downloaded_files", [])
    files_moved = process_moodle_files(downloaded_files)

    downloaded_file_keys = payload.get("downloaded_file_keys", [])
    if downloaded_file_keys:
        _save_ext_downloaded_keys(downloaded_file_keys)

    # 3. Events
    events = payload.get("events", [])
    if not events and not downloaded_files and not downloaded_file_keys:
        return {"status": "success", "message": "Aucune donnée", "inserted": 0, "files_moved": 0}
    
    em = EventManager.instance()
    inserted = 0
    updated = 0
    
    for evt in events:
        uid = evt["id"]
        iso_start = ""
        try:
            if evt.get("timestamp"):
                dt = datetime.fromisoformat(evt["timestamp"].replace("Z", "+00:00"))
                iso_start = dt.isoformat()
        except: pass
            
        if not iso_start:
            iso_start = datetime.now().isoformat()
            
        # create or update event in DB
        existing = em.get_event_by_external_id(uid, "moodle_extension")
        
        event_data = {
            "external_id": uid,
            "source": "moodle_extension",
            "title": evt.get("title", "Sans titre"),
            "start": iso_start,
            "updated": datetime.now().isoformat(),
            "desc_hash": f"moodle_ext_{uid}",
            "category": evt.get("course", "")
        }
        
        if existing:
            em.update_event(existing.id, event_data)
            updated += 1
        else:
            em.create_event(
                external_id=uid,
                source="moodle_extension",
                title=event_data["title"],
                start=event_data["start"],
                updated=event_data["updated"],
                desc_hash=event_data["desc_hash"]
            )
            # Update category for new event
            new_evt = em.get_event_by_external_id(uid, "moodle_extension")
            if new_evt:
                em.update_event(new_evt.id, {"category": event_data["category"]})
            inserted += 1
            
    return {
        "status": "success", 
        "inserted": inserted, 
        "updated": updated,
        "files_moved": files_moved
    }

def get_moodle_extension_events(user_id: str = None) -> list:
    em = EventManager.instance()
    all_events = em.get_all_events(user_id=user_id)
    return [e.to_dict() for e in all_events if e.source == "moodle_extension"]

def get_moodle_extension_courses() -> list:
    return _load_ext_courses()

def get_moodle_sync_state() -> dict:
    with SessionLocal() as db:
        from app.db.models import Event as DBEvent
        event_ids = [e.external_id for e in db.query(DBEvent).filter(DBEvent.source == "moodle_extension").all()]
        file_keys = _load_ext_downloaded_keys()
    
    return {
        "synced_events": event_ids,
        "synced_files": file_keys
    }
