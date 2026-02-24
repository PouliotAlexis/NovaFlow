import json
import os
from datetime import datetime

# Où sauvegarder les événements Moodle envoyés par l'extension
MOODLE_EXT_EVENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "moodle_ext_events.json")

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

def process_extension_payload(payload: dict) -> dict:
    events = payload.get("events", [])
    if not events:
        return {"status": "success", "message": "Aucun événement", "inserted": 0}
    
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
        "updated": updated
    }

def get_moodle_extension_events() -> list:
    """Fonction appelée par calendar_aggregator pour récupérer les événements."""
    return _load_ext_events()
