"""
NovaFlow - Service d'Automatisation (Background Tasks)

Gère les tâches de fond comme l'analyse automatique des documents et événements
pour en extraire des tâches ou des informations pertinentes.
"""

import sys
import asyncio

# Fix pour Windows : Nécessaire pour Playwright (sous-processus)
if sys.platform == "win32":
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import json
import os
import re
import hashlib
from typing import List

from app.core.config import settings
from .document_processor import get_relevant_context, list_documents, extract_text, UPLOADS_DIR
from .ai_engine import chat
from .task_manager import TaskManager, NovaFlowTask
from .calendar_sync.google import get_upcoming_events
from .calendar_sync.outlook import get_outlook_events
from .notification_manager import NotificationManager
from .event_manager import EventManager, NovaFlowEvent
import datetime
import asyncio
import uuid
from .moodle_sync_service import moodle_service
from .moodle_service import sync_moodle_courses


# Logging setup
LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "data", 
    "automation.log"
)

# Gestionnaire de Jobs
active_jobs = {} # id -> {task, name, started_at}

def log_auto(msg: str):
    """Log dans un fichier pour debug."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)


def get_active_jobs():
    """Retourne la liste des jobs en cours."""
    jobs_list = []
    for jid, job in active_jobs.items():
        duration = (datetime.datetime.now() - job["started_at"]).total_seconds()
        jobs_list.append({
            "id": jid,
            "name": job["name"],
            "duration": f"{duration:.1f}s",
            "status": "running"
        })
    return jobs_list


async def cancel_job(job_id: str):
    """Annule un job en cours."""
    if job_id in active_jobs:
        job = active_jobs[job_id]
        job["task"].cancel()
        log_auto(f"⛔ Job annulé par l'utilisateur: {job['name']}")
        try:
            await job["task"]
        except asyncio.CancelledError:
            pass
        return True
    return False


async def start_job(name: str, coro):
    """Lance une coroutine en tant que job tracké."""
    # Pre-check to prevent duplicate jobs
    existing_jobs = get_active_jobs()
    if any(job["name"] == name for job in existing_jobs):
        log_auto(f"⚠️ Le job '{name}' est déjà en cours, annulation du nouveau lancement.")
        return None

    job_id = str(uuid.uuid4())
    
    # Si on passe une fonction (ex: analyze_all_calendars), on l'exécute pour avoir la coroutine
    if callable(coro) and not asyncio.iscoroutine(coro):
        try:
            coro = coro()
        except TypeError:
            # Cas où la fonction attend des arguments obligatoires non fournis
            # On suppose ici que les fonctions passées à start_job ont des valeurs par défaut
            log_auto(f"❌ Erreur: Impossible d'instancier la coroutine pour {name}")
            return None

    try:
        async def wrapper():
            try:
                log_auto(f"🚀 Démarrage job: {name}")
                await coro
                log_auto(f"✨ Job terminé: {name}")
            except asyncio.CancelledError:
                log_auto(f"⛔ Job interrompu: {name}")
                raise
            except Exception as e:
                log_auto(f"💥 Erreur job {name}: {e}")
            finally:
                if job_id in active_jobs:
                    del active_jobs[job_id]

        # On est maintenant dans une fonction async, donc on a une boucle d'événements !
        task = asyncio.create_task(wrapper())
        active_jobs[job_id] = {
            "task": task,
            "name": name,
            "started_at": datetime.datetime.now()
        }
        return job_id
    except Exception as e:
        log_auto(f"CRITICAL ERROR in start_job: {e}")
        return None


def get_recent_logs(lines: int = 5) -> List[str]:
    """Récupère les dernières lignes du log d'automatisation de manière efficace."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        # Lecture par la fin du fichier pour éviter de tout charger en mémoire
        with open(LOG_FILE, "rb") as f:
            try:
                f.seek(0, os.SEEK_END)
                buffer_size = 1024 * 10 # 10 KB devraient suffire pour 5-10 lignes
                if f.tell() < buffer_size:
                    buffer_size = f.tell()
                
                f.seek(-buffer_size, os.SEEK_END)
                chunk = f.read(buffer_size).decode('utf-8', errors='ignore')
                content = chunk.splitlines()
                return content[-lines:]
            except Exception:
                # Fallback si le fichier est trop petit ou erreur seek
                f.seek(0)
                content = f.read().decode('utf-8', errors='ignore').splitlines()
                return content[-lines:]
    except Exception:
        return []


# Fichier pour stocker les IDs des éléments déjà traités (pour éviter les doublons)
PROCESSED_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "data", 
    "processed_items.json"
)

# Timestamp pour le throttling de la synchronisation périodique (Tasks, etc.)
_last_auto_sync_time = datetime.datetime.min

def _load_processed_items() -> dict:
    """Charge l'historique des items traités."""
    if not os.path.exists(PROCESSED_DATA_FILE):
        return {"documents": [], "events": []}
    try:
        with open(PROCESSED_DATA_FILE, "r") as f:
            data = json.load(f)
            
            # Migration: Si events est une liste (ancien format), on convertit en dict
            if isinstance(data.get("events"), list):
                # On met des objets vides pour migration
                new_events = {evt_id: {"updated": "", "start": ""} for evt_id in data["events"]}
                data["events"] = new_events
            
            # Migration 2: Si c'est un dict de chaînes (ancien format intermédiaire)
            elif isinstance(data.get("events"), dict):
                first_val = next(iter(data["events"].values()), None)
                if isinstance(first_val, str):
                    new_events = {}
                    for eid, up in data["events"].items():
                        new_events[eid] = {"updated": up, "start": ""}
                    data["events"] = new_events
                
            return data
    except Exception:
        return {"documents": [], "events": {}}
def _save_processed_items(data: dict):
    """Sauvegarde l'historique des items traités."""
    with open(PROCESSED_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def has_new_events(events: list) -> bool:
    """
    Vérifie s'il y a des événements non traités ou modifiés.
    Supporte les deux sources : Google Calendar et Outlook Calendar.
    """
    try:
        evt_manager = EventManager.instance()
        
        for event in events:
            ext_id = event["id"]
            description = event.get("description", "") or ""
            title = event.get("title", "Sans titre")
            source = event.get("source", "google")
            
            # Skip les events Moodle — ils ne sont pas trackés dans l'EventManager
            if source == "moodle" or source.startswith("moodle"):
                continue
            
            # Mapper la source de l'aggregator vers la source EventManager
            if source == "outlook":
                em_source = "outlook_calendar"
            else:
                em_source = "google_calendar"
            
            # Calculer le hash de la description actuelle
            desc_normalized = re.sub(r'\s+', ' ', description.replace('\r', ' ')).strip()
            current_hash = hashlib.md5(desc_normalized.encode('utf-8')).hexdigest()
            
            nf_event = evt_manager.get_event_by_external_id(ext_id, em_source)
            
            if not nf_event:
                # Nouvel événement non encore tracké
                log_auto(f"DEBUG: New event detected: {title} (source: {em_source})")
                return True
            
            # Vérifier si le contenu a changé
            if nf_event.desc_hash != current_hash or nf_event.title != title:
                log_auto(f"DEBUG: Updated event detected: {title} (source: {em_source})")
                return True
            
            # Vérifier si l'event a une description mais aucune tâche (analyse manquée)
            empty_hash = "d41d8cd98f00b204e9800998ecf8427e"
            if not nf_event.task_ids and current_hash != empty_hash:
                log_auto(f"DEBUG: Event sans tâches détecté: {title} (source: {em_source})")
                return True
        
        # Détection des suppressions — events connus qui ne sont plus dans la liste
        all_nf_events = evt_manager.get_all_events()
        
        # Google
        google_nf_events = {e.external_id: e for e in all_nf_events if e.source == "google_calendar"}
        current_google_ids = {e["id"] for e in events if e.get("source") not in ("outlook", "moodle")}
        
        # Outlook
        outlook_nf_events = {e.external_id: e for e in all_nf_events if e.source == "outlook_calendar"}
        
        current_outlook_ids = set()
        for e in events:
            # Event direct
            if e.get("source") == "outlook":
                current_outlook_ids.add(e["id"])
            # Event fusionné (ex: source="google+outlook") qui contient un ID Outlook lié
            if "linked_outlook_ids" in e:
                for linked_id in e["linked_outlook_ids"]:
                    current_outlook_ids.add(linked_id)
        
        now_dt = datetime.datetime.now()
        now_iso = now_dt.isoformat()
        limit_iso = (now_dt + datetime.timedelta(days=30)).isoformat()
        
        from app.services.calendar_sync.google import is_any_connected as google_is_connected
        from app.services.calendar_sync.microsoft_auth import MicrosoftAuthService

        if google_is_connected():
            for ext_id, nf_event in google_nf_events.items():
                if ext_id not in current_google_ids:
                    start_date = nf_event.start or ""
                    # On ne signale une suppression que si l'event devrait être dans la fenêtre (30 jours)
                    if start_date and (now_iso < start_date < limit_iso):
                        log_auto(f"DEBUG: Deleted Google event detected (id: {ext_id}). Triggering cleanup.")
                        return True
        
        if MicrosoftAuthService.is_any_connected():
            for ext_id, nf_event in outlook_nf_events.items():
                if ext_id not in current_outlook_ids:
                    start_date = nf_event.start or ""
                    if start_date and (now_iso < start_date < limit_iso):
                        log_auto(f"DEBUG: Deleted Outlook event detected (id: {ext_id}). Triggering cleanup.")
                        return True
                
        return False
    except Exception as e:
        log_auto(f"ERROR inside has_new_events: {e}")
        return True  # Default to True on error to be safe

def should_trigger_periodic_sync() -> bool:
    """Vérifie si une synchronisation périodique (Tasks, etc.) est due (toutes les 2 min)."""
    global _last_auto_sync_time
    now = datetime.datetime.now()
    if (now - _last_auto_sync_time).total_seconds() > 120:
        _last_auto_sync_time = now
        log_auto("🕒 Synchronisation périodique des tâches déclenchée (Timeout).")
        return True
    return False


async def analyze_document_for_tasks(doc_id: str, file_name: str):
    """
    Analyse un document après ingestion pour extraire des tâches.
    Cette fonction est conçue pour tourner en BackgroundTask.
    """
    processed = _load_processed_items()
    if doc_id in processed["documents"]:
        return  # Déjà analysé

    try:
        log_auto(f"🔄 [Auto] Analyse du document : {file_name} (ID: {doc_id})")
        
        # 1. Lire le contenu brut du fichier (plus fiable que le RAG pour une analyse globale)
        file_path = os.path.join(UPLOADS_DIR, file_name)
        if not os.path.exists(file_path):
            log_auto(f"⚠️ Fichier introuvable : {file_path}")
            return

        pages = extract_text(file_path)
        if not pages:
            log_auto("⚠️ Pas de texte extrait.")
            return

        # Concaténer les premières pages (max ~4000 caractères pour être safe en local)
        full_text = "\n".join([p["text"] for p in pages])
        truncated_text = full_text[:4000]
        
        log_auto(f"📖 Texte extrait ({len(full_text)} chars), envoi de {len(truncated_text)} chars à l'IA.")

        prompt = (
            f"Tu es un assistant rigoureux. Analyse le document ci-dessous.\n"
            "Ton but est d'extraire UNIQUEMENT les tâches explicitement demandées ou les livrables attendus.\n"
            "Règles CRITIQUES :\n"
            "1. Cherche des mots clés : 'A faire', 'Devoir', 'Projet', 'Deadline', 'Livrables', 'Objectifs'.\n"
            "2. Si tu vois une liste de livrables ou d'étapes de projet, crée une tâche pour chacun.\n"
            "3. N'INVENTE RIEN. Ne crée pas de tâches de 'lecture' ou de 'révision' génériques sauf si c'est demandé.\n"
            "4. Formate CHAQUE tâche trouvée strictement : [TASK: Verbe + Sujet]\n"
            "Exemple : [TASK: Rendre le rapport final]\n"
            "S'il n'y a STRICTEMENT AUCUNE tâche explicite, réponds simplement 'Rien'.\n\n"
            f"--- DÉBUT DOCUMENT ---\n{truncated_text}\n--- FIN DOCUMENT ---"
        )
        
        # System prompt strict
        response = await chat(prompt, system_prompt="Tu es un extracteur de données factuel. Tu ne devines jamais.")
        
        log_auto(f"🤖 Réponse IA :\n{response}")
        
        # Parsing des tâches
        task_pattern = r"\[TASK:\s*(.*?)\]"
        tasks_found = re.findall(task_pattern, response, re.IGNORECASE)
        
        if not tasks_found:
             log_auto("⚠️ Aucune tâche trouvée (Prompt strict).")

        count = 0
        for task_title in tasks_found:
            # Nettoyage basique
            task_title = task_title.strip().strip('"').strip("'")
            TaskManager.instance().add_task(f"{task_title}", priority="medium", meta=f"📄 {file_name}")
            count += 1
            
        NotificationManager.instance().add_notification(
            title="Extraction complète",
            content=f"{count} tâches ont été extraites du document '{file_name}'.",
            type="success" if count > 0 else "info"
        )
        log_auto(f"✅ {count} tâches créées depuis {file_name}")
        
        # Marquer comme traité
        processed["documents"].append(doc_id)
        _save_processed_items(processed)

    except Exception as e:
        log_auto(f"❌ [Auto] Erreur analyse doc {file_name}: {e}")


# EventManager imported at top of file

async def analyze_calendar_for_tasks(events: list = None, days: int = 30, source: str = "google_calendar"):
    """
    Analyse les événements futurs pour suggérer des tâches de préparation.
    Utilise le nouveau système NovaFlowEvent pour la persistance (OOP).
    
    Args:
        events: Liste d'événements déjà récupérés (optionnel).
        days: La fenêtre de temps (en jours) sur laquelle porte le nettoyage.
        source: Source des événements ('google_calendar' ou 'outlook_calendar').
    """
    # Instanciation des Managers
    evt_manager = EventManager.instance()
    task_manager = TaskManager.instance()
    notif_manager = NotificationManager.instance()

    # Si pas d'events fournis, on récupère selon la source
    if events is None:
        if source == "outlook_calendar":
            events = await asyncio.to_thread(get_outlook_events, days=days, max_results=250)
        else:
            events = await asyncio.to_thread(get_upcoming_events, days=days, max_results=250)
        
    source_label = "Outlook" if source == "outlook_calendar" else "Google"
    log_auto(f"📅 Scan: {len(events)} événements {source_label} récupérés.")

    # List to keep track of tasks that need to be re-analyzed by AI
    tasks_to_reanalyze = []

    # 1. Gestion des suppressions (Events NovaFlow qui n'existent plus chez Google)
    # On récupère tous les events connus de source 'google_calendar'
    all_nf_events = evt_manager.get_all_events()
    source_nf_events = {e.external_id: e for e in all_nf_events if e.source == source}
    
    current_google_ids = {e["id"] for e in events}
    
    # Identify orphans
    # NOTE: On ne supprime que si l'event est dans la fenêtre temporelle du scan pour éviter les faux positifs
    # (Ex: un event dans 6 mois qu'on a pas fetché aujourd'hui ne doit pas être supprimé)
    now_dt = datetime.datetime.now()
    limit_dt = now_dt + datetime.timedelta(days=days)
    now_iso = now_dt.isoformat()
    limit_iso = limit_dt.isoformat()
    
    for ext_id, nf_event in source_nf_events.items():
        if ext_id not in current_google_ids:
            # Est-ce que cet event devrait être dans la liste ? (Date de début dans [now, limit])
            start_date = nf_event.start or ""
            if start_date and (now_iso < start_date < limit_iso):
                log_auto(f"🗑️ Event disparu détecté : {nf_event.title} (ID: {ext_id})")
                
                # Récupérer les tâches liées à cet événement qui deviennent orphelines
                for t in task_manager.get_all_tasks():
                    if t.get("parent_event_id") in [nf_event.id, ext_id] and not t.get("done") and t.get("source") in ["microsoft_todo", "google_tasks"]:
                        # Les désolidariser de l'événement
                        task_manager.update_task(t["id"], {"parent_event_id": None})
                        # Les ajouter à la liste de ré-analyse
                        updated_task = task_manager.get_task_object(t["id"])
                        if updated_task:
                            tasks_to_reanalyze.append(updated_task.to_dict())
                        log_auto(f"🔗 Tâche '{t.get('title')}' orpheline suite à la suppression de l'événement.")
                
                evt_manager.delete_event(nf_event.id)

    # 2. Gestion des Ajouts / Modifications
    new_tasks_count = 0
    new_events_added = False
    
    for event in events:
        ext_id = event["id"]
        title = event.get("title", "Sans titre")
        description = event.get("description", "") or ""
        updated = event.get("updated", "")
        start = event.get("start", "")
        
        # Robust normalization for hashing
        desc_normalized = re.sub(r'\s+', ' ', (description or "").replace('\r', ' ')).strip()
        current_hash = hashlib.md5(desc_normalized.encode('utf-8')).hexdigest()
        
        nf_event = evt_manager.get_event_by_external_id(ext_id, source)
        
        should_analyze = False
        
        if not nf_event:
            log_auto(f"🆕 Nouvel événement détecté : {title}")
            
            # Création de l'objet NovaFlowEvent
            nf_event = evt_manager.create_event(
                external_id=ext_id,
                source=source,
                title=title,
                start=start,
                updated=updated,
                desc_hash=current_hash
            )
            should_analyze = True
            new_events_added = True
        else:
            # Vérification des changements
            stored_hash = nf_event.desc_hash
            stored_title = nf_event.title
            
            if stored_hash != current_hash or stored_title != title:
                log_auto(f"🔄 Modification détectée pour : {title}")
                # Mise à jour et Flag pour ré-analyse
                evt_manager.update_event(nf_event.id, {
                    "title": title,
                    "updated": updated,
                    "start": start,
                    "desc_hash": current_hash
                })
                # On nettoie les anciennes tâches avant de ré-analyser
                nf_event.clear_tasks()
                should_analyze = True
            else:
                # Mise à jour mineure (ex: updated timestamp changed but content is same)
                if nf_event.updated != updated:
                    evt_manager.update_event(nf_event.id, {"updated": updated})
                
                # Vérifier si l'event a été traité mais n'a aucune tâche enfant
                # (cas: analyse précédente échouée, interrompue, ou tâches supprimées par le nettoyage)
                if not nf_event.task_ids and description and len(description) > 5:
                    log_auto(f"🔁 Re-analyse requise pour '{title}' (0 tâches, description non-vide)")
                    should_analyze = True

        if should_analyze:
            # --- BLOC ANALYSE IA ---
            try:
                log_auto(f"🔍 Analyse IA pour : {title}")
                
                # Check critical keywords for notification
                lower_title = title.lower()
                critical_keywords = ["examen", "intra", "final", "quiz", "test", "deadline", "remise", "date limite"]
                if any(kw in lower_title for kw in critical_keywords):
                     notif_manager.add_notification(
                        title="Échéance importante",
                        content=f"Rappel : '{title}' approche.",
                        type="deadline"
                    )

                if not description or len(description) <= 5:
                    log_auto(f"ℹ️ Description trop courte pour {title}")
                else:
                    prompt = (
                        f"Voici un événement : '{title}'.\n"
                        f"Description de l'événement :\n---\n{description}\n---\n\n"
                        "Ta mission : Extraire TOUTES les tâches, devoirs, livrables ou éléments à accomplir mentionnés.\n"
                        "Règles :\n"
                        "1. Sois EXTRÊMEMENT permissif.\n"
                        "2. Transforme chaque item en tâche.\n"
                        "3. Ignore uniquement si le texte est purement informatif.\n"
                        "Format : [TASK: Action]\n"
                    )
                    
                    response = await chat(prompt, system_prompt="Assistant extracteur de tâches.")
                    
                    task_pattern = r"\[TASK:\s*(.*?)\]"
                    tasks_found = re.findall(task_pattern, response, re.IGNORECASE)
                    
                    if tasks_found:
                        log_auto(f"✨ {len(tasks_found)} tâches extraites.")
                        for task_title in tasks_found:
                            t_title = task_title.strip()
                            new_task_dict = task_manager.add_task(
                                f"{t_title}", 
                                priority="high", 
                                meta=f"📅 {title}", 
                                parent_event_id=ext_id 
                            )
                            new_task_id = new_task_dict["id"]
                            evt_manager.add_task_to_event(nf_event.id, new_task_id)
                            new_tasks_count += 1
                    else:
                        log_auto(f"ℹ️ Aucun livrable détecté.")
                    
            except Exception as e:
                log_auto(f"❌ Erreur analyse IA : {e}")

    if new_events_added:
        # Trouver toutes les tâches de sources externes qui sont désolidarisées (orphelines) et non complétées
        for t in task_manager.get_all_tasks():
            if not t.get("parent_event_id") and not t.get("done") and t.get("source") in ["microsoft_todo", "google_tasks"]:
                # Éviter les doublons si la tâche a déjà été ajoutée suite à une suppression
                if not any(tr["id"] == t["id"] for tr in tasks_to_reanalyze):
                    tasks_to_reanalyze.append(t)
    
    if tasks_to_reanalyze:
        log_auto(f"🤖 Lancement de l'analyse IA sur {len(tasks_to_reanalyze)} tâches orphelines suite à un événement.")
        await analyze_and_link_tasks(tasks_to_reanalyze)


# === Microsoft To Do et Google Tasks Sync ===

async def sync_microsoft_todo_tasks():
    """
    Tâche de fond : Synchronise les tâches Microsoft To Do.
    Récupère les tâches depuis Graph API et les ajoute/met à jour dans TaskManager.
    Gère aussi les suppressions et modifications.
    """
    log_auto("🔄 Sync Microsoft To Do : Démarrage...")
    from .microsoft_todo import get_todo_tasks
    from fastapi.concurrency import run_in_threadpool
    
    try:
        tasks = await run_in_threadpool(get_todo_tasks)
        if not tasks:
            log_auto("ℹ️ Aucune tâche To Do ou aucun compte connecté.")
            return

        count_new = 0
        count_updated = 0
        count_deleted = 0
        newly_added_tasks = []
        tasks_to_reanalyze = []
        tm = TaskManager.instance()
        all_local_tasks = tm.get_all_tasks()
        
        # Créer un set des IDs externes reçus de la source
        remote_ext_ids = {t_data["id"] for t_data in tasks}
        
        for t_data in tasks:
            existing = next((t for t in all_local_tasks if t.get("external_id") == t_data["id"] and t.get("source") == "microsoft_todo"), None)
            
            if existing:
                # Tâche existante : mettre à jour titre, description, done, due_date si différent
                updates = {}
                if existing.get("title") != t_data["title"]:
                    updates["title"] = t_data["title"]
                if existing.get("done") != t_data["done"]:
                    updates["done"] = t_data["done"]
                if existing.get("due_date") != t_data.get("due_date"):
                    updates["due_date"] = t_data.get("due_date")
                desc = t_data.get("description", "")
                if existing.get("description", "") != desc:
                    updates["description"] = desc
                
                if updates:
                    tm.update_task(existing["id"], updates)
                    count_updated += 1
                    # Si le titre ou la description a changé, relancer l'analyse IA
                    if "title" in updates or "description" in updates:
                        updated_task = tm.get_task_object(existing["id"])
                        if updated_task and not updated_task.done:
                            tasks_to_reanalyze.append(updated_task.to_dict())
            else:
                # Nouvelle tâche
                task_result = tm.add_task(
                    title=t_data["title"],
                    priority=t_data["priority"],
                    meta=t_data["meta"],
                    parent_event_id=None,
                    external_id=t_data["id"],
                    source="microsoft_todo",
                    due_date=t_data.get("due_date")
                )
                task_result["description"] = t_data.get("description", "")
                newly_added_tasks.append(task_result)
                count_new += 1
        
        # Détecter les suppressions : tâches locales To Do qui n'existent plus côté source
        for local_task in all_local_tasks:
            if local_task.get("source") == "microsoft_todo" and local_task.get("external_id"):
                if local_task["external_id"] not in remote_ext_ids:
                    parent_id = local_task.get("parent_event_id")
                    tm.delete_task(local_task["id"])
                    count_deleted += 1
                    log_auto(f"🗑️ Tâche To Do supprimée côté source : '{local_task.get('title')}'")
                    
                    # Si la tâche avait un event IA, vérifier s'il est vide
                    if parent_id:
                        evt_manager = EventManager.instance()
                        old_evt = evt_manager.get_event(parent_id)
                        if old_evt and old_evt.source == "ai_task":
                            other_tasks = [t for t in tm.get_all_tasks() if t.get("parent_event_id") == parent_id]
                            if not other_tasks:
                                evt_manager.delete_event(parent_id)
                                log_auto(f"🗑️ Event IA '{old_evt.title}' supprimé car vide après suppression de la tâche To Do.")
                
        log_auto(f"✅ Sync To Do terminée : {len(tasks)} tâches scannées ({count_updated} màj, {count_new} ajouts, {count_deleted} suppressions).")
        
        all_tasks_for_ai = newly_added_tasks + tasks_to_reanalyze
        if all_tasks_for_ai:
            log_auto(f"🤖 Lancement de l'analyse IA sur {len(all_tasks_for_ai)} tâches To Do (nouvelles + modifiées).")
            await analyze_and_link_tasks(all_tasks_for_ai)
            
    except Exception as e:
        log_auto(f"❌ Erreur Sync Microsoft To Do : {e}")

async def sync_google_tasks():
    """
    Tâche de fond : Synchronise les tâches Google Tasks.
    Gère aussi les suppressions et modifications.
    """
    log_auto("🔄 Sync Google Tasks : Démarrage...")
    from app.services.calendar_sync.google import get_google_tasks
    from fastapi.concurrency import run_in_threadpool
    
    try:
        tasks = await run_in_threadpool(get_google_tasks)
        if not tasks:
            log_auto("ℹ️ Aucune tâche Google Tasks ou aucun compte connecté.")
            return

        count_new = 0
        count_updated = 0
        count_deleted = 0
        newly_added_tasks = []
        tasks_to_reanalyze = []
        tm = TaskManager.instance()
        all_local_tasks = tm.get_all_tasks()
        
        # Créer un set des IDs externes reçus de la source
        remote_ext_ids = {t_data["id"] for t_data in tasks}
        
        for t_data in tasks:
            existing = next((t for t in all_local_tasks if t.get("external_id") == t_data["id"] and t.get("source") == "google_tasks"), None)
            
            if existing:
                # Tâche existante : mettre à jour titre, description, done, due_date si différent
                updates = {}
                if existing.get("title") != t_data["title"]:
                    updates["title"] = t_data["title"]
                if existing.get("done") != t_data["done"]:
                    updates["done"] = t_data["done"]
                if existing.get("due_date") != t_data.get("due_date"):
                    updates["due_date"] = t_data.get("due_date")
                desc = t_data.get("description", "")
                if existing.get("description", "") != desc:
                    updates["description"] = desc
                
                if updates:
                    tm.update_task(existing["id"], updates)
                    count_updated += 1
                    # Si le titre ou la description a changé, relancer l'analyse IA
                    if "title" in updates or "description" in updates:
                        updated_task = tm.get_task_object(existing["id"])
                        if updated_task and not updated_task.done:
                            tasks_to_reanalyze.append(updated_task.to_dict())
            else:
                # Nouvelle tâche
                task_result = tm.add_task(
                    title=t_data["title"],
                    priority=t_data["priority"],
                    meta=t_data["meta"],
                    parent_event_id=None,
                    external_id=t_data["id"],
                    source="google_tasks",
                    due_date=t_data.get("due_date")
                )
                task_result["description"] = t_data.get("description", "")
                newly_added_tasks.append(task_result)
                count_new += 1
        
        # Détecter les suppressions : tâches locales Google Tasks qui n'existent plus côté source
        for local_task in all_local_tasks:
            if local_task.get("source") == "google_tasks" and local_task.get("external_id"):
                if local_task["external_id"] not in remote_ext_ids:
                    parent_id = local_task.get("parent_event_id")
                    tm.delete_task(local_task["id"])
                    count_deleted += 1
                    log_auto(f"🗑️ Tâche Google Tasks supprimée côté source : '{local_task.get('title')}'")
                    
                    # Si la tâche avait un event IA, vérifier s'il est vide
                    if parent_id:
                        evt_manager = EventManager.instance()
                        old_evt = evt_manager.get_event(parent_id)
                        if old_evt and old_evt.source == "ai_task":
                            other_tasks = [t for t in tm.get_all_tasks() if t.get("parent_event_id") == parent_id]
                            if not other_tasks:
                                evt_manager.delete_event(parent_id)
                                log_auto(f"🗑️ Event IA '{old_evt.title}' supprimé car vide après suppression de la tâche Google.")
                
        log_auto(f"✅ Sync Google Tasks terminée : {len(tasks)} tâches scannées ({count_updated} màj, {count_new} ajouts, {count_deleted} suppressions).")
        
        all_tasks_for_ai = newly_added_tasks + tasks_to_reanalyze
        if all_tasks_for_ai:
            log_auto(f"🤖 Lancement de l'analyse IA sur {len(all_tasks_for_ai)} tâches Google (nouvelles + modifiées).")
            await analyze_and_link_tasks(all_tasks_for_ai)
            
    except Exception as e:
        log_auto(f"❌ Erreur Sync Google Tasks : {e}")

async def sync_moodle_native_v2():
    """
    Tâche de fond : Synchronisation profonde de Moodle via Playwright.
    """
    log_auto("🔄 Sync Moodle Native v2 : Démarrage...")
    # Charger le token depuis le fichier de persistance
    token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "moodle_token.json")
    token = None
    if os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)
                token = token_data.get("token")
        except Exception as e:
            log_auto(f"⚠️ Erreur lecture token: {e}")

    if not token:
        log_auto("⚠️ Sync Moodle avortée: Aucun token SSO trouvé. Connecte-toi via le Dashboard.")
        return {"status": "MOODLE_DISCONNECTED", "message": "No token found"}

    try:
        # Url Moodle normalisée
        moodle_url = settings.MOODLE_URL or "https://moodle.usherbrooke.ca"
        
        # Lancer la sync via REST (plus rapide et supporte multi-format + devoirs)
        results = await sync_moodle_courses(
            username=None, 
            password=None, 
            url=moodle_url, 
            token=token
        )
        
        # Calculer les stats
        scanned = len(results)
        synced = len([r for r in results if r.get("status") in ["synced", "synced_no_rag"]])
        
        log_auto(f"✅ Sync Moodle terminée: {synced} fichiers synchronisés ({scanned} scannés).")
        return {
            "status": "SUCCESS", 
            "courses_scanned": scanned, 
            "files_synced": synced,
            "timestamp": datetime.datetime.now()
        }
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        log_auto(f"❌ Erreur Sync Moodle Native v2:\n{err_msg}")
        return {"status": "ERROR", "message": str(e), "trace": err_msg}

async def analyze_and_link_tasks(new_tasks: list):
    """
    Analyse de nouvelles tâches séquentiellement (Une par une) via l'IA locale.
    Privilégie la stabilité et la précision du contexte.
    """
    if not new_tasks: return
        
    evt_manager = EventManager.instance()
    task_manager = TaskManager.instance()
    
    # On importe get_unified_events pour avoir TOUS les events (Moodle, Outlook, Google)
    from app.services.calendar_sync.aggregator import get_unified_events
    import asyncio
    from fastapi.concurrency import run_in_threadpool
    
    try:
        # On regarde jusqu'à 60 jours en avance pour les devoirs lointains
        all_events = await run_in_threadpool(get_unified_events, days=60)
    except Exception as e:
        log_auto(f"Erreur chargement events unifiés pour l'IA: {e}")
        all_events = []
    
    import datetime
    now = datetime.datetime.now()
    today_date_str = now.strftime("%Y-%m-%d")
    now_iso = now.isoformat()
    
    # Filtre de date et Tri
    def get_event_start(e: dict) -> str:
        s = e.get("start", "")
        # Handle dict format from Google Calendar (e.g. {'dateTime': '...', 'date': '...'})
        if isinstance(s, dict):
            return s.get("dateTime") or s.get("date", "")
        return s or ""

    valid_events_raw = [e for e in all_events if get_event_start(e) and get_event_start(e)[:10] >= today_date_str]
    valid_events = sorted(valid_events_raw, key=lambda x: get_event_start(x))[:40]

    # Utiliser un mapping avec des IDs simples pour éviter les hallucinations de l'IA sur des IDs complexes
    # Pour l'assignation finale, on a besoin de l'ID event_manager, ou à défaut l'ID externe.
    event_mapping = {}
    for i, e in enumerate(valid_events):
        idx = str(i+1)
        ext_id = e.get("id")
        source = e.get("source", "google")
        # Map source name back to EventManager source convention
        em_source = "outlook_calendar" if source == "outlook" else source
        if em_source == "google": 
            em_source = "google_calendar"
            
        # Chercher s'il existe déjà dans EventManager
        nf_evt = evt_manager.get_event_by_external_id(ext_id, em_source)
        
        event_mapping[idx] = {
            "title": e.get("title", "Sans titre"),
            "start": get_event_start(e),
            "external_id": ext_id,
            "nf_event": nf_evt,  # Peut être None (ex: Moodle)
            "category": e.get("category", ""),  # Cours Moodle ou autre catégorie
            "course_title": e.get("course_title", "")
        }

    events_text = "\n".join([
        f"- ID: {idx} | Titre: '{e['title']}' | Date: {e['start']}"
        + (f" | Cours: '{e['course_title']}'" if e.get('course_title') else (f" | Cours/Catégorie: '{e['category']}'" if e.get('category') else ""))
        for idx, e in event_mapping.items()
    ])

    log_auto(f"🚀 Analyse séquentielle de {len(new_tasks)} tâches avec l'IA...")
    log_auto(f"ℹ️ Events envoyés à l'IA pour contexte:\n{events_text}")

    for i, task in enumerate(new_tasks):
        task_id = task.get("id")
        title = task.get("title", "Sans titre")
        desc = task.get("description", "")
        due = task.get("due_date")
        meta = task.get("meta", "")
        
        # Construire le contexte de la tâche avec le nom de la liste si disponible
        task_context = f"Tâche: '{title}'"
        if meta:
            task_context += f"\nListe d'origine: {meta}"
        if desc:
            task_context += f"\nDescription: {desc}"
        
        prompt = (
            f"{task_context}\n\n"
            f"Événements existants:\n{events_text}\n\n"
            f"RÈGLES STRICTES DE DÉCISION (SUIS-LES À LA LETTRE):\n"
            f"1. Est-ce que la Tâche partage un MOT-CLÉ TRÈS FORT avec un Événement ? (ex: 'gâteau' = 'Fête', 'devoir' = 'cours', 'neige/ski' = 'Ski Bromont').\n"
            f"   -> Si OUI, choisis 'link'.\n"
            f"   -> Si NON ou dans le DOUTE ABSOLU, passe à la règle 2.\n"
            f"2. Est-ce un NOUVEAU rendez-vous officiel, un vol, une remise de projet importante, ou un examen formel ?\n"
            f"   -> Si OUI, choisis 'create'.\n"
            f"3. DANS TOUS LES AUTRES CAS (Ménage, Vaisselle, Appeler quelqu'un, Acheter des chaussettes, ou si tu hésites), choisis 'none'. C'est le choix par défaut.\n\n"
            f"IMPORTANT: Ne réponds SURTOUT PAS en JSON. Réponds UNIQUEMENT avec ce format texte exact :\n\n"
            f"ACTION: [none, link, ou create]\n"
            f"ID: [ID de l'événement, seulement si link, sinon vide]\n"
            f"TITRE: [Titre du nouvel événement, seulement si create, sinon vide]\n"
            f"DATE: [Date iso, seulement si create, sinon vide]\n"
            f"RAISON: [Pourquoi ?]\n"
        )

        try:
            from app.services.ai_engine import chat as ai_chat
            log_auto(f"⏳ [{i+1}/{len(new_tasks)}] Analyse de '{title}'...")
            raw = await ai_chat(prompt, system_prompt="Tu es un assistant expert et logique. Réponds strictement selon le format texte demandé, sans blabla.")
            
            if "</think>" in raw:
                raw = raw.split("</think>")[-1].strip()
            
            # --- Parsing Textuel Sécurisé ---
            action = "none"
            reasoning = "Pas d'explication"
            event_id = None
            create_title = title
            create_date = due or today_date_str
            
            # Extraction par regex
            action_match = re.search(r"ACTION:\s*(none|link|create)", raw, re.IGNORECASE)
            id_match = re.search(r"ID:\s*([0-9]+)", raw, re.IGNORECASE)
            title_match = re.search(r"TITRE:\s*(.+)", raw, re.IGNORECASE)
            date_match = re.search(r"DATE:\s*([0-9T:Z+-]+)", raw, re.IGNORECASE)
            reason_match = re.search(r"RAISON:\s*(.+)", raw, re.IGNORECASE)
            
            if action_match:
                action = action_match.group(1).lower().strip()
            if reason_match:
                reasoning = reason_match.group(1).strip()
            
            res = {"action": action, "reasoning": reasoning}
            
            if action == "link" and id_match:
                res["event_id"] = id_match.group(1).strip()
            if action == "create" and title_match:
                # Éviter que l'IA ne répète le template vide "[Titre...]"
                t_val = title_match.group(1).strip()
                if not t_val.startswith("["):
                    res["title"] = t_val
            if action == "create" and date_match:
                d_val = date_match.group(1).strip()
                if not d_val.startswith("["):    
                    res["date"] = d_val
                    
            log_auto(f"🧠 IA Reasoning: {reasoning}")
            
            old_parent_id = task.get("parent_event_id")
            new_parent_id = None
            
            if action == "link":
                mapped_id = str(res.get("event_id", ""))
                # Validation stricte en Python : vérifie si l'ID inventé est réel
                if mapped_id in event_mapping:
                    event_data = event_mapping[mapped_id]
                    nf_evt = event_data["nf_event"]
                    # S'il n'y a pas d'événement NovaFlow (ex: Moodle pur), on doit le créer d'abord pour avoir un parent interne ?
                    # TaskManager gère parent_event_id. On peut stocker l'external_id de Moodle comme parent. L'aggrégateur s'en occupe
                    new_parent_id = nf_evt.id if nf_evt else event_data["external_id"]
                    linked_title = event_data.get('title', 'Inconnu')
                    log_auto(f"✅ Linked: '{title}' -> Événement [{mapped_id}] '{linked_title}'")
                else:
                    action = "none" # Fallback si l'IA hallucine un ID
                    log_auto(f"⚠️  Hallucination ID détectée pour '{title}': {mapped_id}. Rejeté.")

            elif action == "create":
                new_title = res.get("title") or title
                new_date = res.get("date") or due or today_date_str
                import uuid
                new_evt = evt_manager.create_event(str(uuid.uuid4()), "ai_task", new_title, new_date, now_iso, "")
                new_parent_id = new_evt.id
                log_auto(f"✅ Created: '{title}' -> Nouvel événement '{new_title}' le {new_date}")
            else:
                log_auto(f"ℹ️ Orphan: '{title}'")
                
            # Mettre à jour la BD seulement si le parent a changé
            if old_parent_id != new_parent_id:
                if new_parent_id is not None:
                    task_manager.link_task_to_event(task_id, new_parent_id)
                else:
                    task_manager.update_task(task_id, {"parent_event_id": None})
                    
                # Si l'ancienne tâche était liée à un événement purement IA, vérifier s'il est maintenant vide
                if old_parent_id:
                    old_evt = evt_manager.get_event(old_parent_id)
                    if old_evt and old_evt.source == "ai_task":
                        other_tasks = [t for t in task_manager.get_all_tasks() if t.get("parent_event_id") == old_parent_id and t.get("id") != task_id]
                        if not other_tasks:
                            evt_manager.delete_event(old_parent_id)
                            log_auto(f"🗑️ Nettoyage de l'ancien event IA '{old_evt.title}' devenu vide suite à la ré-analyse de '{title}'.")
                
        except Exception as e:
            log_auto(f"❌ Error for '{title}': {e} - Raw: {raw[:100] if 'raw' in locals() else 'N/A'}")

async def analyze_all_calendars(days: int = 30):
    """Analyse les événements de toutes les sources (Google + Outlook + To Do)."""
    # 1. Google (seulement si connecté)
    from app.services.calendar_sync.google import is_any_connected as google_is_connected
    if google_is_connected():
        await analyze_calendar_for_tasks(events=None, days=days, source="google_calendar")
        await sync_google_tasks()
    
    # 2. Outlook (si connecté)
    from app.services.calendar_sync.microsoft_auth import MicrosoftAuthService
    if MicrosoftAuthService.is_any_connected():
        await analyze_calendar_for_tasks(events=None, days=days, source="outlook_calendar")

    # 3. Microsoft To Do (si connecté)
    await sync_microsoft_todo_tasks()

