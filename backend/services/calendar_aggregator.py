from typing import List, Dict, Any
from difflib import SequenceMatcher
from services.google_service import get_upcoming_events
from services.microsoft_calendar import get_outlook_events
from services.task_manager import TaskManager

def _dedup_key(title: str, start: str) -> str:
    """Crée une clé de déduplication normalisant titre + heure de début."""
    clean_title = (title or "").strip().lower()
    clean_start = (start or "")[:16]  # YYYY-MM-DDTHH:MM (ignore les secondes)
    return f"{clean_title}|{clean_start}"


def _is_similar_task(title_a: str, title_b: str, threshold: float = 0.75) -> bool:
    """Vérifie si deux titres de tâches sont sémantiquement similaires."""
    a = (title_a or "").strip().lower()
    b = (title_b or "").strip().lower()
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= threshold


def _merge_tasks(existing_tasks: list, new_tasks: list) -> list:
    """
    Fusionne deux listes de tâches en évitant les doublons sémantiques.
    Les tâches existantes (Google) ont priorité. Les nouvelles (Outlook) ne sont
    ajoutées que si aucune tâche existante ne leur ressemble suffisamment.
    """
    merged = list(existing_tasks)
    for new_task in new_tasks:
        is_duplicate = any(
            _is_similar_task(new_task.get("title", ""), ex.get("title", ""))
            for ex in merged
        )
        if not is_duplicate:
            merged.append(new_task)
    return merged


def get_unified_events(days: int = 30) -> List[Dict[str, Any]]:
    """
    Récupère et unifie les événements de toutes les sources (Google, Outlook, local, etc.)
    et y injecte les tâches associées.
    Déduplique les événements identiques entre sources (même titre + même heure).
    """
    # 1. Récupérer les événements Google
    try:
        google_events = get_upcoming_events(days=days)
    except Exception as e:
        print(f"Erreur récupération Google: {e}")
        google_events = []

    # 2. Récupérer les événements Outlook
    try:
        outlook_events = get_outlook_events(days=days)
    except Exception as e:
        print(f"Erreur récupération Outlook: {e}")
        outlook_events = []

    # 3. Récupérer toutes les tâches NovaFlow
    tm = TaskManager.instance()
    all_tasks = tm.get_all_tasks()
    
    # 4. Organiser les tâches par parent_event_id pour un accès rapide
    tasks_by_event = {}
    for task in all_tasks:
        parent_id = task.get("parent_event_id")
        if parent_id:
            if parent_id not in tasks_by_event:
                tasks_by_event[parent_id] = []
            tasks_by_event[parent_id].append(task)

    # 5. Indexer les événements Google (prioritaires) par clé de dédup
    dedup_index: Dict[str, Dict[str, Any]] = {}
    unified_events = []

    for g_event in google_events:
        event_id = g_event["id"]
        title = g_event.get("title", "Sans titre")
        start = g_event.get("start", "")
        dk = _dedup_key(title, start)

        unified_event = {
            "id": event_id,
            "title": title,
            "start": start,
            "end": g_event.get("end"),
            "location": g_event.get("location", ""),
            "description": g_event.get("description", ""),
            "all_day": g_event.get("all_day", False),
            "link": g_event.get("link", ""),
            "accounts": g_event.get("accounts", []),
            "source": "google",
            "tasks": tasks_by_event.get(event_id, [])
        }
        dedup_index[dk] = unified_event
        unified_events.append(unified_event)

    # 6. Ajouter les événements Outlook, en fusionnant si doublon
    for o_event in outlook_events:
        event_id = o_event["id"]
        title = o_event.get("title", "Sans titre")
        start = o_event.get("start", "")
        dk = _dedup_key(title, start)

        if dk in dedup_index:
            # Doublon détecté — fusionner dans l'event Google existant
            existing = dedup_index[dk]
            existing["source"] = "google+outlook"
            # Ajouter les comptes Outlook sans dupliquer
            for acct in o_event.get("accounts", []):
                if acct not in existing["accounts"]:
                    existing["accounts"].append(acct)
            # Fusionner les tâches (dédup par similarité de titre, pas juste par ID)
            outlook_tasks = tasks_by_event.get(event_id, [])
            if outlook_tasks:
                existing["tasks"] = _merge_tasks(existing["tasks"], outlook_tasks)
        else:
            # Événement Outlook unique
            unified_event = {
                "id": event_id,
                "title": title,
                "start": start,
                "end": o_event.get("end"),
                "location": o_event.get("location", ""),
                "description": o_event.get("description", ""),
                "all_day": o_event.get("all_day", False),
                "link": o_event.get("link", ""),
                "accounts": o_event.get("accounts", []),
                "source": "outlook",
                "tasks": tasks_by_event.get(event_id, [])
            }
            dedup_index[dk] = unified_event
            unified_events.append(unified_event)

    # 7. Trier par date de début
    unified_events.sort(key=lambda x: x["start"] or "")
    
    return unified_events

