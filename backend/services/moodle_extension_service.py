import json
import os
import shutil
from datetime import datetime

# Où sauvegarder les événements Moodle envoyés par l'extension
MOODLE_EXT_EVENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "moodle_ext_events.json")
MOODLE_EXT_COURSES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "moodle_ext_courses.json")

def _ensure_data_dir():
    os.makedirs(os.path.dirname(MOODLE_EXT_EVENTS_FILE), exist_ok=True)

def _load_ext_events():
    _ensure_data_dir()
    if os.path.exists(MOODLE_EXT_EVENTS_FILE):
        try:
            with open(MOODLE_EXT_EVENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _save_ext_events(events):
    _ensure_data_dir()
    with open(MOODLE_EXT_EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

def _save_ext_courses(courses):
    _ensure_data_dir()
    with open(MOODLE_EXT_COURSES_FILE, "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

def _load_ext_courses():
    if os.path.exists(MOODLE_EXT_COURSES_FILE):
        try:
            with open(MOODLE_EXT_COURSES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def process_moodle_files(downloaded_files: list):
    """
    Checks if the files sent by the extension exist in the Downloads folder
    and moves them to the permanent NovaFlow_Courses directory.
    """
    if not downloaded_files:
        return 0
        
    from core.config import settings
    
    downloads_dir = os.path.expanduser("~/Downloads")
    target_base = settings.MOODLE_DOWNLOADS_DESTINATION
    
    moved_count = 0
    
    for relative_path in downloaded_files:
        # relative_path is something like "NovaFlow_Moodle/CourseA/Section1/File.pdf"
        # We only want to process files originating from NovaFlow_Moodle
        if not relative_path.startswith("NovaFlow_Moodle"):
            continue
            
        source_path = os.path.join(downloads_dir, relative_path)
        
        # Check if the file is fully downloaded
        if os.path.exists(source_path):
            # Also check if it's currently being downloaded (Chrome uses .crdownload)
            if os.path.exists(source_path + ".crdownload"):
                continue # Skip for now, will get picked up next sync
                
            # Determine target path
            # Remove "NovaFlow_Moodle/" from the start to avoid redundant nesting
            clean_rel_path = relative_path.replace("NovaFlow_Moodle/", "", 1)
            target_path = os.path.join(target_base, clean_rel_path)
            
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            try:
                # Move the file (overwrites if it exists in dest)
                shutil.move(source_path, target_path)
                moved_count += 1
                print(f"✅ Moved Moodle file: {target_path}")
            except Exception as e:
                print(f"❌ Failed to move Moodle file {source_path}: {e}")
                
    return moved_count

def process_extension_payload(payload: dict) -> dict:
    courses = payload.get("courses", [])
    if courses:
        _save_ext_courses(courses)
        
    downloaded_files = payload.get("downloaded_files", [])
    files_moved = process_moodle_files(downloaded_files)

    events = payload.get("events", [])
    if not events and not downloaded_files:
        return {"status": "success", "message": "Aucune donnée (events/fichiers)", "inserted": 0, "files_moved": 0}
    
    # Charger les événements existants
    existing_events = _load_ext_events()
    existing_by_id = {e["id"]: e for e in existing_events}
    
    inserted = 0
    updated = 0
    
    for evt in events:
        uid = evt["id"]
        # Format "Standard" pour l'EventManager / CalendarAggregator de NovaFlow
        # On essaie d'extraire la date du timestamp et sinon on fallback sur un ISO bidon + due_date_text
        
        iso_start = ""
        iso_end = ""
        is_all_day = False
        
        try:
            # Si le dom a fourni un datetime ISO valide
            if evt.get("timestamp"):
                dt = datetime.fromisoformat(evt["timestamp"].replace("Z", "+00:00"))
                iso_start = dt.isoformat()
                iso_end = iso_start
        except:
            pass
            
        if not iso_start:
            # Fallback très très brut : utiliser today pour l'afficher au moins 
            # (Dans un vrai scrapper, on parserait "lundi, 25 mars")
            iso_start = datetime.now().isoformat()
            iso_end = iso_start
            is_all_day = True
            
        account_label = f"Moodle — {evt.get('organization', 'Extension')}"

        standardized_event = {
            "id": uid,
            "title": evt.get("title", 'Sans titre'),
            "start": iso_start,
            "end": iso_end,
            "description": f"Extrait via NovaFlow Sync : {evt.get('due_date_text', '')}",
            "location": evt.get("course", ""),
            "all_day": is_all_day,
            "link": evt.get("link", ""),
            "category": evt.get("course", ""),
            "accounts": [account_label],
            "source": "moodle_extension"
        }
        
        if uid in existing_by_id:
            existing_by_id[uid].update(standardized_event)
            updated += 1
        else:
            existing_by_id[uid] = standardized_event
            inserted += 1
            
    _save_ext_events(list(existing_by_id.values()))
    
    return {
        "status": "success", 
        "message": f"Synchronisation réussie", 
        "inserted": inserted, 
        "updated": updated,
        "files_moved": files_moved
    }

def get_moodle_extension_events() -> list:
    """Fonction appelée par calendar_aggregator pour récupérer les événements."""
    return _load_ext_events()

def get_moodle_extension_courses() -> list:
    """Fonction appelée par calendar_aggregator pour récupérer le dictionnaire parfait de cours."""
    return _load_ext_courses()
