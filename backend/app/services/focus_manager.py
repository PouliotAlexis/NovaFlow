import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

FOCUS_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "focus_sessions.json")

def _load_sessions() -> List[Dict[str, Any]]:
    if not os.path.exists(FOCUS_DATA_FILE):
        return []
    try:
        with open(FOCUS_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def _save_sessions(sessions: List[Dict[str, Any]]):
    with open(FOCUS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=4)

def start_focus_session(task_id: Optional[str] = None, task_title: Optional[str] = None) -> Dict[str, Any]:
    """Démarre une nouvelle session de focus."""
    sessions = _load_sessions()
    
    new_session = {
        "id": str(uuid.uuid4()),
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "duration_minutes": 0,
        "task_id": task_id,
        "task_title": task_title,
        "active": True
    }
    
    # S'assurer qu'il n'y a qu'une seule session active
    for s in sessions:
        if s.get("active"):
            s["active"] = False
            if not s["end_time"]:
                s["end_time"] = datetime.now().isoformat()
    
    sessions.insert(0, new_session)
    _save_sessions(sessions)
    return new_session

def stop_focus_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Termine une session de focus active."""
    sessions = _load_sessions()
    for s in sessions:
        if s["id"] == session_id:
            s["active"] = False
            s["end_time"] = datetime.now().isoformat()
            
            # Calculer la durée
            start = datetime.fromisoformat(s["start_time"])
            end = datetime.fromisoformat(s["end_time"])
            s["duration_minutes"] = round((end - start).total_seconds() / 60, 2)
            
            _save_sessions(sessions)
            return s
    return None

def get_focus_stats() -> Dict[str, Any]:
    """Récupère les statistiques de focus."""
    sessions = _load_sessions()
    
    total_minutes = sum(s.get("duration_minutes", 0) for s in sessions if not s.get("active"))
    session_count = len([s for s in sessions if not s.get("active")])
    
    # Stats par jour (7 derniers jours)
    daily_stats = {}
    for s in sessions:
        if s.get("active"): continue
        day = s["start_time"].split("T")[0]
        daily_stats[day] = daily_stats.get(day, 0) + s.get("duration_minutes", 0)
    
    return {
        "total_minutes": round(total_minutes, 2),
        "session_count": session_count,
        "daily_stats": daily_stats,
        "recent_sessions": sessions[:10]
    }
