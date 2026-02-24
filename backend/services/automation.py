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
from services.microsoft_calendar import get_outlook_events
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


async def start_job(name: str, coro):
    """Lance une coroutine en tant que job tracké."""
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
        
        from services.google_service import is_any_connected as google_is_connected
        from services.microsoft_auth import MicrosoftAuthService

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


# === Microsoft To Do Sync ===

async def sync_microsoft_todo_tasks():
    """
    Tâche de fond : Synchronise les tâches Microsoft To Do.
    Récupère les tâches depuis Graph API et les ajoute/met à jour dans TaskManager.
    """
    log_auto("🔄 Sync Microsoft To Do : Démarrage...")
    from services.microsoft_todo import get_todo_tasks
    from fastapi.concurrency import run_in_threadpool
    
    try:
        # Exécuter l'appel bloquant requests dans un thread
        tasks = await run_in_threadpool(get_todo_tasks)
        
        if not tasks:
            log_auto("ℹ️ Aucune tâche To Do ou aucun compte connecté.")
            return

        count_new = 0
        count_updated = 0
        
        for t_data in tasks:
            # data from get_todo_tasks: 
            # {id, title, priority, meta, done, parent_event_id, created_at, source, link, description}
            
            # 1. Tenter d'ajouter (dédoublonnage via external_id dans add_task)
            # Note: add_task retourne le dict de la tâche (nouvelle ou existante)
            task_result = task_manager.add_task(
                title=t_data["title"],
                priority=t_data["priority"],
                meta=t_data["meta"],
                parent_event_id=None,
                external_id=t_data["id"],
                source="microsoft_todo"
            )
            
            # 2. Vérifier si on doit mettre à jour le statut 'done'
            # (Si la tâche existait déjà mais que son statut local diffère du remote)
            # Ici t_data['done'] vient de Microsoft. 
            # task_result['done'] est la valeur locale.
            
            # Simple sync: Remote wins for status
            if task_result["done"] != t_data["done"]:
                task_manager.update_task(task_result["id"], {"done": t_data["done"]})
                count_updated += 1
            
            # On pourrait aussi sync le titre si changé, mais attention aux écrasements locaux.
            # Pour l'instant on sync juste le statut.
            
            # Si la tâche a été créée (on check si created_at est très récent ou si on avait pas cet ID avant)
            # Mais add_task ne dit pas explicitement "created".
            # On suppose que c'est un flux continu.
            
        log_auto(f"✅ Sync To Do terminée : {len(tasks)} tâches scannées ({count_updated} màj statut).")
        
    except Exception as e:
        log_auto(f"❌ Erreur Sync Microsoft To Do : {e}")




async def analyze_all_calendars(days: int = 30):
    """Analyse les événements de toutes les sources (Google + Outlook + To Do)."""
    # 1. Google (seulement si connecté)
    from services.google_service import is_any_connected as google_is_connected
    if google_is_connected():
        await analyze_calendar_for_tasks(events=None, days=days, source="google_calendar")
    
    # 2. Outlook (si connecté)
    from services.microsoft_auth import MicrosoftAuthService
    if MicrosoftAuthService.is_any_connected():
        await analyze_calendar_for_tasks(events=None, days=days, source="outlook_calendar")

    # 3. Microsoft To Do (si connecté)
    # La fonction gère elle-même la vérification des comptes
    await sync_microsoft_todo_tasks()
