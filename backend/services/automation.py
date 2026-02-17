"""
NovaFlow - Service d'Automatisation (Background Tasks)

Gère les tâches de fond comme l'analyse automatique des documents et événements
pour en extraire des tâches ou des informations pertinentes.
"""

import json
import os
import re
import hashlib
from typing import List

from services.document_processor import get_relevant_context, list_documents, extract_text, UPLOADS_DIR
from services.ai_engine import chat
from services.task_manager import TaskManager, NovaFlowTask
from services.google_service import get_upcoming_events
from services.notification_manager import NotificationManager
from services.event_manager import EventManager, NovaFlowEvent
import datetime
import asyncio
import uuid

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


def start_job(name: str, coro):
    """Lance une coroutine en tant que job tracké."""
    job_id = str(uuid.uuid4())
    
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

        task = asyncio.create_task(wrapper())
        active_jobs[job_id] = {
            "task": task,
            "name": name,
            "started_at": datetime.datetime.now()
        }
        return job_id
    except Exception as e:
        log_auto(f"CRICAL ERROR in start_job: {e}")
        return None


def get_recent_logs(lines: int = 5) -> List[str]:
    """Récupère les dernières lignes du log d'automatisation."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read().splitlines()
            return content[-lines:]
    except Exception:
        return []

# Fichier pour stocker les IDs des éléments déjà traités (pour éviter les doublons)
PROCESSED_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "data", 
    "processed_items.json"
)

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
    Utilise EventManager comme source de vérité (plus de processed_items.json pour les events).
    """
    try:
        evt_manager = EventManager.instance()
        
        for event in events:
            ext_id = event["id"]
            description = event.get("description", "") or ""
            title = event.get("title", "Sans titre")
            
            # Calculer le hash de la description actuelle
            desc_normalized = re.sub(r'\s+', ' ', description.replace('\r', ' ')).strip()
            current_hash = hashlib.md5(desc_normalized.encode('utf-8')).hexdigest()
            
            nf_event = evt_manager.get_event_by_external_id(ext_id, "google_calendar")
            
            if not nf_event:
                # Nouvel événement non encore tracké
                log_auto(f"DEBUG: New event detected: {title}")
                return True
            
            # Vérifier si le contenu a changé
            if nf_event.desc_hash != current_hash or nf_event.title != title:
                log_auto(f"DEBUG: Updated event detected: {title}")
                return True
        
        # Détection des suppressions — events connus qui ne sont plus dans la liste Google
        all_nf_events = evt_manager.get_all_events()
        google_nf_events = {e.external_id: e for e in all_nf_events if e.source == "google_calendar"}
        current_google_ids = {e["id"] for e in events}
        
        now_iso = datetime.datetime.now().isoformat()
        for ext_id, nf_event in google_nf_events.items():
            if ext_id not in current_google_ids:
                start_date = nf_event.start or ""
                if not start_date or start_date > now_iso:
                    log_auto(f"DEBUG: Deleted event detected (id: {ext_id}). Triggering cleanup.")
                    return True
                
        return False
    except Exception as e:
        log_auto(f"ERROR inside has_new_events: {e}")
        return True  # Default to True on error to be safe


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

async def analyze_calendar_for_tasks(events: list = None, days: int = 30):
    """
    Analyse les événements futurs pour suggérer des tâches de préparation.
    Utilise le nouveau système NovaFlowEvent pour la persistance (OOP).
    
    Args:
        events: Liste d'événements déjà récupérés (optionnel).
        days: La fenêtre de temps (en jours) sur laquelle porte le nettoyage.
    """
    # Instanciation des Managers
    evt_manager = EventManager.instance()
    task_manager = TaskManager.instance()
    notif_manager = NotificationManager.instance()

    # Si pas d'events fournis, on récupère un range par défaut (30j)
    if events is None:
        events = await asyncio.to_thread(get_upcoming_events, days=days, max_results=250)
        
    log_auto(f"📅 Scan: {len(events)} événements Google récupérés.")

    # 1. Gestion des suppressions (Events NovaFlow qui n'existent plus chez Google)
    # On récupère tous les events connus de source 'google_calendar'
    all_nf_events = evt_manager.get_all_events()
    google_nf_events = {e.external_id: e for e in all_nf_events if e.source == "google_calendar"}
    
    current_google_ids = {e["id"] for e in events}
    
    # Identify orphans
    # NOTE: On ne supprime que si l'event est dans la fenêtre temporelle du scan pour éviter les faux positifs
    # (Ex: un event dans 6 mois qu'on a pas fetché aujourd'hui ne doit pas être supprimé)
    now_dt = datetime.datetime.now()
    limit_dt = now_dt + datetime.timedelta(days=days)
    now_iso = now_dt.isoformat()
    limit_iso = limit_dt.isoformat()
    
    for ext_id, nf_event in google_nf_events.items():
        if ext_id not in current_google_ids:
            # Est-ce que cet event devrait être dans la liste ? (Date de début dans [now, limit])
            start_date = nf_event.start or ""
            if start_date and (now_iso < start_date < limit_iso):
                log_auto(f"🗑️ Event disparu détecté : {nf_event.title} (ID: {ext_id})")
                evt_manager.delete_event(nf_event.id)

    # 2. Gestion des Ajouts / Modifications
    new_tasks_count = 0
    
    for event in events:
        ext_id = event["id"]
        title = event.get("title", "Sans titre")
        description = event.get("description", "") or ""
        updated = event.get("updated", "")
        start = event.get("start", "")
        
        # Robust normalization for hashing
        desc_normalized = re.sub(r'\s+', ' ', (description or "").replace('\r', ' ')).strip()
        current_hash = hashlib.md5(desc_normalized.encode('utf-8')).hexdigest()
        
        nf_event = evt_manager.get_event_by_external_id(ext_id, "google_calendar")
        
        should_analyze = False
        
        if not nf_event:
            log_auto(f"🆕 Nouvel événement détecté : {title}")
            
            # Création de l'objet NovaFlowEvent
            nf_event = evt_manager.create_event(
                external_id=ext_id,
                source="google_calendar",
                title=title,
                start=start,
                updated=updated,
                desc_hash=current_hash
            )
            should_analyze = True
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
                # Mise à jour mineure (ex: updated timestamp changed but content is same, or just a heartbeat)
                if nf_event.updated != updated:
                    evt_manager.update_event(nf_event.id, {"updated": updated})
                # Skip AI
                pass

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

                if description and len(description) > 5:
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
                            # Création de la tâche via TaskManager
                            t_title = task_title.strip()
                            # Utilisation de l'instance TaskManager
                            new_task_dict = task_manager.add_task(
                                f"{t_title}", 
                                priority="high", 
                                meta=f"📅 {title}", 
                                parent_event_id=ext_id 
                            )
                            # Récupération de l'ID depuis le dict retourné
                            new_task_id = new_task_dict["id"]
                            
                            # Lier la tâche à l'événement NovaFlow
                            # En OOP, on appelle la méthode sur l'objet event
                            nf_event.add_task(new_task_id)
                            
                            # Sauvegarder l'état de l'event (add_task modifie l'objet en mémoire, faut persister)
                            # Note: EventManager.add_task_to_event le fait, mais ici on a l'objet.
                            # Idéalement 'nf_event.add_task' devrait être suivi d'un save ou être géré par le manager.
                            # Dans ma refactor EventManager, add_task_to_event fait le job.
                            # On va utiliser le manager pour être sûr de la persistance immédiate.
                            evt_manager.add_task_to_event(nf_event.id, new_task_id)
                            
                            new_tasks_count += 1
                    else:
                        log_auto(f"ℹ️ Aucun livrable détecté.")
                else:
                    log_auto(f"ℹ️ Description vide ou courte.")
                    
            except Exception as e:
                log_auto(f"❌ Erreur analyse IA : {e}")

    if new_tasks_count > 0:
        log_auto(f"✅ Cycle terminé. {new_tasks_count} nouvelles tâches.")
    else:
        log_auto("✅ Cycle terminé. Aucun changement majeur.")
