from typing import List, Dict, Any
from services.google_service import get_upcoming_events
from services.task_manager import TaskManager

def get_unified_events(days: int = 30) -> List[Dict[str, Any]]:
    """
    Récupère et unifie les événements de toutes les sources (Google, local, etc.)
    et y injecte les tâches associées.
    """
    # 1. Récupérer les événements Google
    try:
        google_events = get_upcoming_events(days=days)
    except Exception as e:
        print(f"Erreur graduation Google: {e}")
        google_events = []

    # 2. Récupérer toutes les tâches NovaFlow
    tm = TaskManager.instance()
    all_tasks = tm.get_all_tasks()
    
    # 3. Organiser les tâches par parent_event_id pour un accès rapide
    tasks_by_event = {}
    for task in all_tasks:
        parent_id = task.get("parent_event_id")
        if parent_id:
            if parent_id not in tasks_by_event:
                tasks_by_event[parent_id] = []
            tasks_by_event[parent_id].append(task)

    # 4. Unifier et enrichir
    unified_events = []
    for g_event in google_events:
        event_id = g_event["id"]
        
        # Structure de base unifiée
        unified_event = {
            "id": event_id,
            "title": g_event.get("title", "Sans titre"),
            "start": g_event.get("start"),
            "end": g_event.get("end"),
            "location": g_event.get("location", ""),
            "description": g_event.get("description", ""),
            "all_day": g_event.get("all_day", False),
            "link": g_event.get("link", ""),
            "accounts": g_event.get("accounts", []),
            "source": "google",
            "tasks": tasks_by_event.get(event_id, [])
        }
        unified_events.append(unified_event)

    # 5. TODO: Ajouter les événements 100% locaux si nécessaire
    
    # Trier par date de début
    unified_events.sort(key=lambda x: x["start"])
    
    return unified_events
