from typing import List, Dict, Any
from difflib import SequenceMatcher
from services.google_service import get_upcoming_events
from services.microsoft_calendar import get_outlook_events
from services.moodle_rss_service import get_moodle_events
from services.moodle_extension_service import get_moodle_extension_events, get_moodle_extension_courses
from services.task_manager import TaskManager
from services.event_manager import EventManager
import os
import json

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

    # 3. Récupérer les événements Moodle (multi-URL)
    moodle_events = []
    moodle_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "moodle_settings.json")
    if os.path.exists(moodle_file):
        try:
            with open(moodle_file, "r", encoding="utf-8") as f:
                moodle_settings = json.load(f)
                # Support nouveau format {urls: [...]} et ancien {url: "..."}
                urls = moodle_settings.get("urls", [])
                if not urls:
                    old_url = moodle_settings.get("url")
                    if old_url:
                        urls = [old_url]
                for moodle_url in urls:
                    if moodle_url:
                        try:
                            moodle_events.extend(get_moodle_events(moodle_url, days=days))
                        except Exception as e:
                            print(f"Erreur Moodle URL {moodle_url[:50]}: {e}")
        except Exception as e:
            print(f"Erreur récupération Moodle: {e}")

    # 4. Récupérer les événements de l'Extension Naviguateur Moodle
    moodle_ext_events = []
    try:
        moodle_ext_events = get_moodle_extension_events()
    except Exception as e:
        print(f"Erreur Moodle Extension: {e}")

    # 4.5 Récupérer les événements locaux (AI, etc.)
    local_nf_events = []
    try:
        em = EventManager.instance()
        # On ne prend que les events locaux/AI qui ne sont pas déjà des miroirs de Google/Outlook
        # (ceux-ci sont déjà gérés via les API respectives et le lien parent_event_id)
        all_em_events = em.get_all_events()
        for e in all_em_events:
            if e.source not in ("google_calendar", "outlook_calendar", "moodle"):
                local_nf_events.append(e.to_dict())
    except Exception as e:
        print(f"Erreur Events Locaux: {e}")

    # Créer un dictionnaire parfait pour mapper les codes de cours (ex: "PHQ202") vers leur nom complet
    course_code_to_name = {}
    try:
        ext_courses = get_moodle_extension_courses()
        for course in ext_courses:
            shortname = course.get("shortname", "")
            fullname = course.get("fullname", "")
            if shortname and fullname:
                # Stocker le shortname exact (ex: "PHQ334-AB")
                course_code_to_name[shortname] = fullname
                # Stocker aussi le code de base pour la robustesse (ex: "PHQ334")
                base_code = shortname.split('-')[0]
                course_code_to_name[base_code] = fullname
    except Exception as e:
        print(f"Erreur chargement des cours Moodle Extension: {e}")

    # 5. Récupérer toutes les tâches NovaFlow
    tm = TaskManager.instance()
    em = EventManager.instance()
    all_tasks = tm.get_all_tasks()
    
    # 6. Organiser les tâches par parent_event_id pour un accès rapide
    # On supporte l'ID externe (préféré) ET l'ID interne (fallback pour robustesse)
    tasks_by_event = {}
    for task in all_tasks:
        parent_id = task.get("parent_event_id")
        if parent_id:
            # 1. Essai direct (ID externe ou ID déjà correct)
            if parent_id not in tasks_by_event:
                tasks_by_event[parent_id] = []
            tasks_by_event[parent_id].append(task)
            
            # 2. Fallback: Si parent_id est un UUID interne, mapper aussi vers l'ID externe
            # de l'événement pour que l'agrégateur puisse le trouver
            if "-" in parent_id and len(parent_id) > 20: # Probablement un UUID NovaFlow
                evt = em.get_event(parent_id)
                if evt and evt.external_id:
                    ext_id = evt.external_id
                    if ext_id not in tasks_by_event:
                        tasks_by_event[ext_id] = []
                    # Éviter les doublons si l'ID externe était déjà dans la liste
                    if task not in tasks_by_event[ext_id]:
                        tasks_by_event[ext_id].append(task)

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
            
            # Stocker l'ID Outlook original pour éviter qu'il soit considéré comme supprimé par l'automation
            if "linked_outlook_ids" not in existing:
                existing["linked_outlook_ids"] = []
            if event_id not in existing["linked_outlook_ids"]:
                existing["linked_outlook_ids"].append(event_id)
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

    # 7. Ajouter les événements Moodle
    for m_event in moodle_events:
        event_id = m_event["id"]
        title = m_event.get("title", "Sans titre")
        start = m_event.get("start", "")
        dk = _dedup_key(title, start)

        # Essayer d'enrichir la catégorie de l'événement Moodle (iCal) avec le nom complet de l'extension
        current_cat = m_event.get("category", "")
        if current_cat:
            # Chercher si un code de cours connu est dans la catégorie iCal (ex: "PHQ202" dans "Automne 2024-PHQ202")
            for code, full_name in course_code_to_name.items():
                if code in current_cat or code in title:
                    m_event["category"] = full_name
                    break

        if dk in dedup_index:
            existing = dedup_index[dk]
            if "moodle" not in existing["source"]:
                existing["source"] += "+moodle"
            for acct in m_event.get("accounts", []):
                if acct not in existing["accounts"]:
                    existing["accounts"].append(acct)
            # Mettre à jour la catégorie si on a trouvé un meilleur nom
            if m_event.get("category") and (not existing.get("category") or len(m_event.get("category")) > len(existing.get("category"))):
                existing["category"] = m_event.get("category")
        else:
            unified_event = m_event.copy()
            unified_event["tasks"] = tasks_by_event.get(event_id, [])
            dedup_index[dk] = unified_event
            unified_events.append(unified_event)

    # 8. Ajouter les événements de l'Extension Moodle
    for ext_evt in moodle_ext_events:
        event_id = ext_evt["id"]
        title = ext_evt.get("title", "Sans titre")
        start = ext_evt.get("start", "")
        dk = _dedup_key(title, start)

        if dk in dedup_index:
            existing = dedup_index[dk]
            if "extension" not in str(existing.get("source")):
                existing["source"] = f"{existing.get('source', '')}+moodle_extension"
            for acct in ext_evt.get("accounts", []):
                if acct not in existing.get("accounts", []):
                    existing["accounts"].append(acct)
            # Favorise le lien de l'extension car il est direct vers le devoir
            if ext_evt.get("link"):
                existing["link"] = ext_evt.get("link")
        else:
            unified_event = ext_evt.copy()
            unified_event["tasks"] = tasks_by_event.get(event_id, [])
            dedup_index[dk] = unified_event
            unified_events.append(unified_event)

    # 9. Ajouter les événements locaux NovaFlow
    for l_evt in local_nf_events:
        event_id = l_evt["id"]
        title = l_evt.get("title", "Sans titre")
        start = l_evt.get("start", "")
        dk = _dedup_key(title, start)

        if dk not in dedup_index:
            unified_event = l_evt.copy()
            unified_event["source"] = l_evt.get("source", "local")
            unified_event["tasks"] = tasks_by_event.get(event_id, [])
            dedup_index[dk] = unified_event
            unified_events.append(unified_event)

    # 10. Trier par date de début
    unified_events.sort(key=lambda x: x["start"] or "")
    
    return unified_events

