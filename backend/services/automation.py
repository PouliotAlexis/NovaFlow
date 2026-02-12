"""
NovaFlow - Service d'Automatisation (Background Tasks)

Gère les tâches de fond comme l'analyse automatique des documents et événements
pour en extraire des tâches ou des informations pertinentes.
"""

import json
import os
import re
from typing import List

from services.document_processor import get_relevant_context, list_documents, extract_text, UPLOADS_DIR
from services.ai_engine import chat
from services.task_manager import add_task, get_tasks
from services.google_calendar import get_upcoming_events
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
                # On met des timestamps vides pour forcer la ré-analyse au moins une fois
                new_events = {evt_id: "" for evt_id in data["events"]}
                data["events"] = new_events
                
            return data
    except Exception:
        return {"documents": [], "events": {}}
def _save_processed_items(data: dict):
    """Sauvegarde l'historique des items traités."""
    with open(PROCESSED_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def has_new_events(events: list) -> bool:
    """Vérifie s'il y a des événements non traités ou modifiés."""
    try:
        processed = _load_processed_items()
        processed_events = processed.get("events", {})
        
        # log_auto(f"DEBUG: Checking {len(events)} events against {len(processed_events)} processed items.")
        
        for event in events:
            evt_id = event["id"]
            updated = event.get("updated", "")
            
            # Si l'événement est nouveau OU s'il a été mis à jour plus récemment
            if evt_id not in processed_events:
                log_auto(f"DEBUG: New event detected: {event.get('title')}")
                return True
            if processed_events[evt_id] != updated:
                log_auto(f"DEBUG: Updated event detected: {event.get('title')}")
                return True
                
        return False
    except Exception as e:
        log_auto(f"ERROR inside has_new_events: {e}")
        return True # Default to True on error to be safe


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
            add_task(f"{task_title}", priority="medium", meta=f"📄 {file_name}")
            count += 1
            
        log_auto(f"✅ {count} tâches créées depuis {file_name}")
        
        # Marquer comme traité
        processed["documents"].append(doc_id)
        _save_processed_items(processed)

    except Exception as e:
        log_auto(f"❌ [Auto] Erreur analyse doc {file_name}: {e}")


async def analyze_calendar_for_tasks(events: list = None):
    """
    Analyse les événements futurs pour suggérer des tâches de préparation.
    """
    processed = _load_processed_items()
    # Migration défensive si nécessaire
    if isinstance(processed.get("events"), list):
         processed["events"] = {eid: "" for eid in processed["events"]}
         
    # Si pas d'events fournis, on récupère un range large par défaut (30j)
    if events is None:
        events = await asyncio.to_thread(get_upcoming_events, days=30, max_results=50)
    
    new_tasks_count = 0
    
    for event in events:
        evt_id = event["id"]
        updated = event.get("updated", "")
        
        # Vérification si déjà traité ET non modifié
        if evt_id in processed["events"] and processed["events"][evt_id] == updated:
            continue
            
        try:
            # Analyse simple par mots-clés pour commencer (plus rapide que l'IA pour chaque event)
            # Ou utilisation de l'IA pour décider
            
            title = event.get("title", "")
            desc = event.get("description", "")
            
            # On ne déclenche l'IA que si la description contient des indices de tâches
            # Pour éviter d'inventer des prépas pour chaque cours
            
            prompt = (
                f"Voici un événement : '{title}'.\n"
                f"Description : {desc}\n\n"
                "Ta mission : Identifier s'il y a des sous-tâches EXPLICITEMENT listées dans la description.\n"
                "Règles :\n"
                "1. Ne devine pas de préparation (ex: ne dis pas 'Réviser' juste parce que c'est un examen, sauf si c'est écrit).\n"
                "2. Si la description contient une liste de choses à faire (ex: 'Apporter X', 'Finir Y'), crée une tâche pour chaque item.\n"
                "3. Si la description est vide ou ne contient pas d'ordres, réponds 'NON'.\n"
                "Format : [TASK: Action]\n"
            )
            
            # Filtrage pré-IA pour économiser et éviter le bruit
            # On envoie à l'IA seulement si la description n'est pas vide
            if desc and len(desc) > 5:
                response = await chat(prompt, system_prompt="Tu es un assistant factuel. Tu ne crées des tâches que si elles sont écrites.")
                
                task_pattern = r"\[TASK:\s*(.*?)\]"
                tasks_found = re.findall(task_pattern, response)
                
                for task_title in tasks_found:
                    add_task(f"{task_title}", priority="high", meta=f"📅 {title}")
                    new_tasks_count += 1
            
            # Marquer comme traité avec le timestamp
            processed["events"][evt_id] = updated
            _save_processed_items(processed)
            log_auto(f"✅ Event {event.get('title')} traité et sauvegardé.")
            
        except Exception as e:
            print(f"❌ [Auto] Erreur analyse event {evt_id}: {e}")
            
    # Toujours sauvegarder pour ne pas perdre les timestamps (et éviter de ré-analyser en boucle)
    _save_processed_items(processed)
    
    if new_tasks_count > 0:
        print(f"✅ [Auto] {new_tasks_count} tâches calendrier créées.")
