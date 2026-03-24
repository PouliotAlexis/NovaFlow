"""
NovaFlow API - Point d'entrée principal

Ce fichier définit toutes les routes de l'API FastAPI.
"""

import sys
import os
import shutil
from datetime import datetime
import asyncio
import json


from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, List

from app.core.config import settings
from app.services.sanitizer import sanitize, desanitize, SanitizationMap
from app.services.ai_engine import chat, chat_stream
from app.services.document_processor import (
    ingest_document,
    get_relevant_context,
    list_documents,
    delete_document,
    UPLOADS_DIR,
)
from app.services.calendar_sync.google import (
    get_auth_url,
    handle_callback,
    is_any_connected as google_is_connected,
    disconnect_account as google_disconnect,
    get_upcoming_events,
    get_today_events,
    list_connected_accounts
)
from app.services.calendar_sync.microsoft_auth import MicrosoftAuthService
from app.services.task_manager import TaskManager, NovaFlowTask
from app.services.event_manager import EventManager
import re
from app.services.automation import (
    analyze_document_for_tasks, 
    analyze_calendar_for_tasks,
    analyze_all_calendars,
    get_recent_logs,
    start_job,
    cancel_job,
    get_active_jobs,
    has_new_events
)
from app.services.chat_manager import load_chat_history, save_chat_message, clear_chat_history
from app.services.notification_manager import NotificationManager
from app.api.routes import chat as chat_router
from app.api.routes import moodle as moodle_router

# === App Setup ===

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="NovaFlow - Votre Life OS intelligent et privé.",
)

# Inclusion des nouveaux routers
app.include_router(chat_router.router, prefix="/api/v2", tags=["Chat V2"])
app.include_router(moodle_router.router, prefix="/api/v2", tags=["Moodle V2"])

# Managers Instances
task_manager = TaskManager.instance()
notif_manager = NotificationManager.instance()

# CORS - Permettre au Frontend Next.js de communiquer avec le Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Modèles de données (Pydantic) ===

class ChatRequest(BaseModel):
    """Requête envoyée par le frontend pour parler à l'IA."""
    message: str
    system_prompt: Optional[str] = ""
    mode: Optional[str] = None  # "local" ou "cloud", None = config par défaut
    sensitive_entities: Optional[List[str]] = None  # Entités à censurer manuellement
    use_rag: Optional[bool] = True  # Utiliser la recherche documentaire
    course_id: Optional[str] = None  # ID du cours pour association auto des tâches


class TaskRequest(BaseModel):
    title: str


class ChatResponse(BaseModel):
    """Réponse de l'IA renvoyée au frontend."""
    response: str
    mode_used: str
    was_sanitized: bool
    context_used: bool = False
    sanitization_map: Optional[dict] = None  # Pour le debug uniquement


class HealthCheck(BaseModel):
    status: str = "ok"
    app_name: str = settings.APP_NAME
    version: str = settings.APP_VERSION
    ai_mode: str = settings.AI_MODE


# === Routes ===

@app.get("/")
def read_root():
    return {
        "message": f"Bienvenue sur {settings.APP_NAME} API 🚀",
        "version": settings.APP_VERSION,
        "ai_mode": settings.AI_MODE,
    }

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Route fantôme pour éviter les erreurs 404 du navigateur."""
    from fastapi import Response
    return Response(status_code=204)


@app.get("/health", response_model=HealthCheck)
def health_check():
    """Vérifie que le serveur est en marche."""
    return HealthCheck()


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint principal de chat avec l'IA.
    
    Recherche automatiquement le contexte pertinent dans les documents
    ingérés (RAG) pour enrichir la réponse de l'IA.
    """
    active_mode = request.mode or settings.AI_MODE
    was_sanitized = False
    san_map = None
    context = ""

    prompt = request.message
    
    # Sauvegarder le message utilisateur dans l'historique
    save_chat_message("user", prompt)

    # Recherche de contexte RAG dans les documents (Optimisation: n_results=2)
    if request.use_rag:
        try:
            context = get_relevant_context(prompt, n_results=2)
        except Exception:
            context = ""

    # Si mode Cloud, sanitizer le message AVANT l'envoi
    if active_mode == "cloud":
        prompt, san_map = sanitize(prompt, request.sensitive_entities)
        if context:
            context, _ = sanitize(context)  # Sanitizer aussi le contexte
        was_sanitized = True

        # Récupération events Google Calendar (si connecté) - Optimisation: 7 jours max
    if google_is_connected():
        try:
            # Réduire à 7 jours et 20 résultats max pour éviter de bloquer trop longtemps
            events = get_upcoming_events(days=7, max_results=20)
            if events:
                cal_ctx = "\n\n## Mon Calendrier (7 prochains jours)\n"
                for evt in events:
                    start_str = f"{evt['start'].replace('T', ' ')}"
                    end_str = f"{evt['end'].replace('T', ' ')}" if evt.get('end') else ""
                    time_info = "Journée enitère" if evt.get('all_day') else f"{start_str} -> {end_str}"
                    cal_ctx += f"- {evt['title']} ({time_info})\n"
                    if evt.get('description'):
                        cal_ctx += f"  Desc: {evt['description']}\n"
                context += cal_ctx
        except Exception as e:
            print(f"Erreur injection calendrier: {e}")

    try:
        # Envoyer à l'IA avec le contexte
        ai_response = await chat(
            prompt=prompt,
            system_prompt=request.system_prompt or "",
            mode=active_mode,
            context=context,
        )

        # Si sanitizé, restaurer les vraies valeurs dans la réponse
        if was_sanitized and san_map:
            ai_response = desanitize(ai_response, san_map)

        # Post-process : Détection de commandes (Tool Calling)
        # Format attendu : [TASK: Titre de la tâche]
        task_pattern = r"\[TASK:\s*(.*?)\]"
        
        # Détection du cours si non fourni explicitement
        course_id = request.course_id
        if not course_id:
            course_id = EventManager.instance().find_course_id_by_text(prompt) or \
                        EventManager.instance().find_course_id_by_text(ai_response)
        
        parent_id = None
        if course_id:
            parent_id = EventManager.instance().get_or_create_course_event(course_id)

        # Remplacement robuste via regex
        def create_and_confirm_task(match):
            task_title = match.group(1).strip()
            print(f"✨ AI Action: Creating task '{task_title}' (Course: {course_id})")
            
            # Créer la tâche
            task_manager.add_task(
                title=task_title, 
                priority="medium", 
                meta=f"AI Generated ({course_id or 'Global'})",
                parent_event_id=parent_id
            )
            
            # Envoyer une notification pour feedback immédiat
            notif_manager.add_notification(
                title="Nouvelle tâche",
                content=f"L'IA a créé la tâche : {task_title}" + (f" (Cours: {course_id})" if course_id else ""),
                type="success"
            )
            
            return f"✅ Tâche '{task_title}' ajoutée."

        ai_response = re.sub(task_pattern, create_and_confirm_task, ai_response, flags=re.IGNORECASE)

        # Sauvegarder la réponse IA dans l'historique
        save_chat_message("ai", ai_response)

        return ChatResponse(
            response=ai_response,
            mode_used=active_mode,
            was_sanitized=was_sanitized,
            context_used=bool(context),
            sanitization_map=san_map.token_map if san_map and settings.DEBUG else None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la communication avec l'IA ({active_mode}): {str(e)}",
        )


@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Endpoint de chat avec réponse en streaming (Server-Sent Events).
    Envoie les tokens au fur et à mesure, puis un événement 'done' final
    avec la réponse post-traitée (détection de commandes, desanitization).
    """
    active_mode = request.mode or settings.AI_MODE
    was_sanitized = False
    san_map = None
    context = ""
    prompt = request.message

    # Recherche de contexte RAG
    if request.use_rag:
        try:
            context = get_relevant_context(prompt, n_results=2)
        except Exception:
            context = ""

    # Sanitization cloud
    if active_mode == "cloud":
        prompt, san_map = sanitize(prompt, request.sensitive_entities)
        if context:
            context, _ = sanitize(context)
        was_sanitized = True

    # Injection calendrier Google
    if google_is_connected():
        try:
            events = get_upcoming_events(days=7, max_results=20)
            if events:
                cal_ctx = "\n\n## Mon Calendrier (7 prochains jours)\n"
                for evt in events:
                    start_str = f"{evt['start'].replace('T', ' ')}"
                    end_str = f"{evt['end'].replace('T', ' ')}" if evt.get('end') else ""
                    time_info = "Journée entière" if evt.get('all_day') else f"{start_str} -> {end_str}"
                    cal_ctx += f"- {evt['title']} ({time_info})\n"
                    if evt.get('description'):
                        cal_ctx += f"  Desc: {evt['description']}\n"
                context += cal_ctx
        except Exception as e:
            print(f"Erreur injection calendrier (stream): {e}")

    save_chat_message("user", prompt if not was_sanitized else request.message)

    async def generate():
        full_response = ""
        try:
            async for token in chat_stream(
                prompt=prompt,
                system_prompt=request.system_prompt or "",
                mode=active_mode,
                context=context,
            ):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # Post-traitement sur la réponse complète
        processed = full_response
        if was_sanitized and san_map:
            processed = desanitize(processed, san_map)

        task_pattern = r"\[TASK:\s*(.*?)\]"
        
        # Détection du cours si non fourni
        course_id = request.course_id
        if not course_id:
            course_id = EventManager.instance().find_course_id_by_text(prompt) or \
                        EventManager.instance().find_course_id_by_text(processed)

        parent_id = None
        if course_id:
            parent_id = EventManager.instance().get_or_create_course_event(course_id)

        # Remplacement robuste via regex
        def create_and_confirm_task_stream(match):
            task_title = match.group(1).strip()
            print(f"✨ AI Stream Action: Creating task '{task_title}' (Course: {course_id})")
            
            # Créer la tâche
            task_manager.add_task(
                title=task_title, 
                priority="medium", 
                meta=f"AI Generated ({course_id or 'Global'})",
                parent_event_id=parent_id
            )
            
            # Envoyer une notification pour feedback immédiat
            notif_manager.add_notification(
                title="Nouvelle tâche",
                content=f"L'IA a créé la tâche : {task_title}" + (f" (Cours: {course_id})" if course_id else ""),
                type="success"
            )
            
            return f"✅ Tâche '{task_title}' ajoutée."

        processed = re.sub(task_pattern, create_and_confirm_task_stream, processed, flags=re.IGNORECASE)

        save_chat_message("ai", processed)

        yield f"data: {json.dumps({'type': 'done', 'response': processed, 'mode_used': active_mode, 'context_used': bool(context)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# === Endpoints Chat History ===

@app.get("/api/chat/history")
def get_chat_history():
    """Récupère l'historique des conversations."""
    return {"history": load_chat_history()}

@app.delete("/api/chat/history")
def delete_chat_history():
    """Efface l'historique des conversations."""
    clear_chat_history()
    return {"status": "cleared"}


# === Endpoints Documents (RAG) ===

@app.post("/api/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload et ingère un document.
    
    Le fichier est sauvegardé, son texte est extrait, découpé en chunks
    et stocké dans ChromaDB pour la recherche contextuelle.
    """
    # Vérifier le type de fichier
    allowed_extensions = {".pdf", ".txt", ".md", ".csv"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté : {ext}. Formats acceptés : {', '.join(allowed_extensions)}",
        )
    
    # Sauvegarder le fichier
    file_path = os.path.join(UPLOADS_DIR, file.filename or "uploaded_file")
    
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la sauvegarde : {str(e)}")
    
    # Ingérer le document
    result = ingest_document(file_path, file.filename or "uploaded_file")
    
    # ⚡ AUTOMATION: Lancer l'analyse en tant que Job tracké
    if result["status"] == "analyzed":
        await start_job(
            f"Analyse doc: {result['file_name']}",
            analyze_document_for_tasks(
                doc_id=result["doc_id"], 
                file_name=result["file_name"]
            )
        )
    
    return result


@app.get("/api/documents")
def get_documents():
    """Liste tous les documents ingérés."""
    return {"documents": list_documents()}


@app.delete("/api/documents/{doc_id}")
def remove_document(doc_id: str):
    """Supprime un document de la base vectorielle."""
    success = delete_document(doc_id)
    if success:
        return {"status": "deleted", "doc_id": doc_id}
    raise HTTPException(status_code=404, detail="Document non trouvé.")


@app.get("/api/documents/{doc_id}/download")
def download_document(doc_id: str):
    """Télécharge/ouvre un document uploadé."""
    docs = list_documents()
    doc = next((d for d in docs if d["doc_id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé.")
    
    file_path = os.path.join(UPLOADS_DIR, doc["file_name"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé sur le disque.")
    
    return FileResponse(
        path=file_path,
        filename=doc["file_name"],
        media_type="application/octet-stream",
    )


@app.get("/api/settings")
def get_settings():
    """Retourne les paramètres actuels (non sensibles)."""
    return {
        "ai_mode": settings.AI_MODE,
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_host": settings.OLLAMA_HOST,
        "openai_model": settings.OPENAI_MODEL,
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "google_calendar_connected": google_is_connected(),
    }


# === Moodle Settings ===

MOODLE_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "moodle_settings.json")

def _load_moodle_urls() -> list:
    """Charge les URLs Moodle. Compatible ancien format {url} et nouveau {urls}."""
    if os.path.exists(MOODLE_SETTINGS_FILE):
        try:
            with open(MOODLE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "urls" in data:
                    return [u for u in data["urls"] if u]
                old_url = data.get("url", "")
                if old_url:
                    return [old_url]
        except Exception:
            pass
    return []

def _save_moodle_urls(urls: list):
    with open(MOODLE_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"urls": urls}, f, indent=2)

@app.get("/api/settings/moodle")
def get_moodle_settings():
    urls = _load_moodle_urls()
    return {"urls": urls, "url": urls[0] if urls else ""}

class MoodleAddUrl(BaseModel):
    url: str

@app.post("/api/settings/moodle")
def save_moodle_settings(settings: MoodleAddUrl):
    urls = _load_moodle_urls()
    if settings.url and settings.url not in urls:
        urls.append(settings.url)
    _save_moodle_urls(urls)
    return {"status": "success", "urls": urls}

@app.delete("/api/settings/moodle")
def delete_moodle_url(url: str):
    urls = _load_moodle_urls()
    urls = [u for u in urls if u != url]
    _save_moodle_urls(urls)
    return {"status": "success", "urls": urls}

# === Extension Moodle ===
from typing import Any, Dict

class MoodleExtensionSync(BaseModel):
    source: str
    timestamp: str
    events: list[Dict[str, Any]]
    courses: Optional[list[Dict[str, Any]]] = []
    downloaded_files: Optional[list[str]] = []
    downloaded_file_keys: Optional[list[str]] = []

@app.get("/api/moodle/sync/state")
def get_moodle_sync_state_endpoint():
    from app.services.moodle_extension_service import get_moodle_sync_state
    return get_moodle_sync_state()

@app.post("/api/moodle/sync")
def sync_moodle_events(payload: MoodleExtensionSync):
    from app.services.moodle_extension_service import process_extension_payload
    return process_extension_payload(payload.model_dump())

@app.post("/api/settings/moodle/test")
def test_moodle_url():
    """Teste toutes les URLs Moodle configurées."""
    urls = _load_moodle_urls()
    if not urls:
        return {"status": "error", "message": "Aucune URL Moodle configurée.", "events_count": 0}
    
    import requests as req
    from app.services.moodle_rss_service import get_moodle_events
    
    total_events = 0
    errors = []
    for url in urls:
        try:
            r = req.get(url, timeout=15, allow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NovaFlow/1.0"
            })
            if r.status_code != 200:
                errors.append(f"HTTP {r.status_code}")
                continue
            events = get_moodle_events(url, days=30)
            total_events += len(events)
        except Exception as e:
            errors.append(str(e)[:50])
    
    if total_events > 0:
        msg = f"{total_events} événements trouvés sur {len(urls)} calendrier(s)."
        return {"status": "ok", "message": msg, "events_count": total_events}
    elif errors:
        return {"status": "error", "message": " | ".join(errors), "events_count": 0}
    else:
        return {"status": "warning", "message": "Aucun événement dans les 30 prochains jours.", "events_count": 0}

# === Google Calendar OAuth ===

@app.get("/api/auth/google/login")
def google_login():
    """Retourne l'URL de connexion Google."""
    return {"url": get_auth_url()}


@app.get("/api/auth/google/callback")
def google_callback(code: str):
    """Callback OAuth Google."""
    return handle_callback(code)


@app.get("/api/auth/google/accounts")
def google_accounts():
    """Liste les comptes Google connectés."""
    return {"accounts": list_connected_accounts()}


@app.delete("/api/auth/google/accounts/{email}")
def google_disconnect_account(email: str):
    """Déconnecte un compte spécifique."""
    if google_disconnect(email):
        return {"status": "disconnected"}
    raise HTTPException(status_code=404, detail="Compte non trouvé")


@app.get("/api/auth/google/status")
def google_status():
    """Vérifie si au moins un compte est connecté."""
    return {"connected": google_is_connected()}


@app.get("/api/auth/google/disconnect")
def google_disconnect_all():
    """Déconnecte TOUS les comptes Google (pour compatibilité)."""
    accounts = list_connected_accounts()
    for acc in accounts:
        google_disconnect(acc)
    return {"status": "all_disconnected"}


# === Microsoft Azure OAuth ===

@app.get("/api/auth/microsoft/login")
def microsoft_login():
    """Retourne l'URL de connexion Microsoft."""
    auth_service = MicrosoftAuthService()
    return {"url": auth_service.get_auth_url()}


@app.get("/api/auth/microsoft/callback")
def microsoft_callback(code: str):
    """Callback OAuth Microsoft - retourne une page HTML qui se ferme automatiquement."""
    from fastapi.responses import HTMLResponse
    
    auth_service = MicrosoftAuthService()
    result = auth_service.acquire_token_by_code(code)
    
    if "error" in result:
        html = f"""
        <html><body style="background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif">
            <div style="text-align:center">
                <h2>❌ Connection failed</h2>
                <p>{result.get('error_description', 'Unknown error')}</p>
                <p style="color:#888">You can close this window.</p>
            </div>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=400)
    
    email = result.get("email", "")
    html = f"""
    <html><body style="background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif">
        <div style="text-align:center">
            <h2>✅ Microsoft connected!</h2>
            <p>Account: <strong>{email}</strong></p>
            <p style="color:#888">This window will close automatically...</p>
        </div>
        <script>setTimeout(() => window.close(), 1500);</script>
    </body></html>
    """
    return HTMLResponse(content=html)


@app.get("/api/auth/microsoft/accounts")
def microsoft_accounts():
    """Liste les comptes Microsoft connectés."""
    return {"accounts": MicrosoftAuthService.list_connected_accounts()}


@app.delete("/api/auth/microsoft/accounts/{email}")
def microsoft_disconnect(email: str):
    """Déconnecte un compte Microsoft spécifique."""
    if MicrosoftAuthService.disconnect_account(email):
        return {"status": "disconnected"}
    raise HTTPException(status_code=404, detail="Compte non trouvé")


@app.get("/api/auth/microsoft/status")
def microsoft_status():
    """Vérifie si au moins un compte Microsoft est connecté."""
    return {"connected": MicrosoftAuthService.is_any_connected()}


@app.get("/api/automation/logs")
def get_automation_logs():
    """Récupère les logs récents de l'automatisation."""
    logs = get_recent_logs(lines=5)
    return {"logs": logs}

@app.get("/api/automation/jobs")
def get_automation_jobs():
    """Récupère la liste des jobs en cours."""
    return get_active_jobs()

@app.delete("/api/automation/jobs/{job_id}")
async def cancel_automation_job(job_id: str):
    """Annule un job en cours."""
    success = await cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job non trouvé ou déjà terminé")
    return {"status": "cancelled"}


# === Endpoints Tâches ===

@app.get("/api/tasks")
async def get_all_tasks():
    """Récupère toutes les tâches."""
    # ⚡ AUTOMATION — Déclencher l'analyse périodique (Tasks) si nécessaire
    try:
        from app.services.automation import should_trigger_periodic_sync, analyze_all_calendars, get_active_jobs, start_job
        existing_jobs = get_active_jobs()
        is_running = any(job["name"] == "Analyse Calendrier" for job in existing_jobs)
        if not is_running and should_trigger_periodic_sync():
             await start_job("Analyse Calendrier", analyze_all_calendars(days=30))
    except Exception as e:
        print(f"Erreur déclenchement sync depuis tasks api: {e}")
        
    return task_manager.get_all_tasks()

@app.post("/api/tasks")
def create_new_task(task: TaskRequest):
    """Crée une nouvelle tâche."""
    return task_manager.add_task(task.title, priority="medium", meta="Utilisateur")

@app.patch("/api/tasks/{task_id}/toggle")
def toggle_task_status(task_id: str):
    """Inverse le statut d'une tâche."""
    result = task_manager.toggle_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    return result

@app.patch("/api/tasks/{task_id}")
async def update_existing_task(task_id: str, updates: dict, background_tasks: BackgroundTasks):
    """Modifie une tâche et vérifie s'il faut reclassifier."""
    old_task = task_manager.get_task_object(task_id)
    if not old_task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
        
    old_parent_id = old_task.parent_event_id
    
    # Mettre à jour la tâche
    result = task_manager.update_task(task_id, updates)
    new_parent_id = updates.get("parent_event_id", old_parent_id)
    
    # Si le parent_event_id a changé, on met à jour les événements
    if "parent_event_id" in updates and new_parent_id != old_parent_id:
        from app.services.event_manager import EventManager
        em = EventManager.instance()
        
        # Enlever de l'ancien event
        if old_parent_id:
            old_evt = em.get_event(old_parent_id) or em.get_event_by_external_id(old_parent_id, old_task.source)
            if old_evt:
                em.remove_task_from_event(old_evt.id, task_id)
                
                # Nettoyer l'événement si vide et créé par l'IA
                other_tasks = [t for t in task_manager.get_all_tasks() if t.get("parent_event_id") == old_parent_id and t["id"] != task_id]
                if not other_tasks and old_evt.source == "ai_task":
                    import app.services.automation as auto
                    auto.log_auto(f"🗑️ Nettoyage de l'event IA '{old_evt.title}' suite au changement de parent_event_id de sa tâche.")
                    em.delete_event(old_evt.id)
                    
        # Ajouter au nouvel event
        if new_parent_id:
            # Note: The frontend might send an external_id or an internal event_id. 
            # We try to get the event by ID directly, or fallback to external_id if possible. 
            # Assuming frontend sends the internal ID of the NovaFlowEvent for simplicity if it's from localEvents.
            new_evt = em.get_event(new_parent_id)
            if new_evt:
                em.add_task_to_event(new_evt.id, task_id)
            else:
                 # It might be an external ID from a raw aggregator source
                 new_evt = em.get_event_by_external_id(new_parent_id, "google_calendar") or em.get_event_by_external_id(new_parent_id, "outlook_calendar")
                 if new_evt:
                     em.add_task_to_event(new_evt.id, task_id)
                     # Optional: Update the task to use the internal ID for consistency
                     task_manager.update_task(task_id, {"parent_event_id": new_evt.id})
    
    # Si on a modifié le titre ou la date, on lance une analyse IA en arrière plan
    # (Seulement si on n'a pas explicitement changé le parent manuellement)
    if ("title" in updates or "due_date" in updates or "description" in updates) and "parent_event_id" not in updates:
        from app.services.automation import analyze_and_link_tasks
        updated_task = task_manager.get_task_object(task_id)
        if updated_task and not updated_task.done:
             background_tasks.add_task(analyze_and_link_tasks, [updated_task.to_dict()])
             
    return result

@app.post("/api/tasks/{task_id}/force-create-event")
def force_create_event_for_task(task_id: str):
    """Force la création d'un événement calendrier pour une tâche orpheline."""
    task = task_manager.get_task_object(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
        
    old_parent_id = task.parent_event_id
    from app.services.event_manager import EventManager
    import app.services.automation as auto
    import uuid
    from datetime import datetime
    
    em = EventManager.instance()
    
    # Check if task already has a parent event
    if old_parent_id:
        old_evt = em.get_event(old_parent_id) or em.get_event_by_external_id(old_parent_id, task.source)
        if old_evt:
             raise HTTPException(status_code=400, detail="Cette tâche est déjà liée à un événement.")
             
    new_title = task.title + " ✨"
    new_date = task.due_date or datetime.now().isoformat()
    now_iso = datetime.now().isoformat()
    new_evt_id = str(uuid.uuid4())
    
    new_evt = em.create_event(
        external_id=new_evt_id,
        source="ai_task",
        title=new_title,
        start=new_date,
        updated=now_iso,
        desc_hash=""
    )
    
    # Link the task
    task_manager.update_task(task_id, {"parent_event_id": new_evt.id})
    em.add_task_to_event(new_evt.id, task_id)
    
    auto.log_auto(f"✅ Forced creation of event '{new_title}' for task '{task.title}'")
    
    return {"status": "success", "event": new_evt.to_dict(), "task": task_manager.get_task_object(task_id).to_dict()}

@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: str):
    """Supprime une tâche."""
    task = task_manager.get_task_object(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
        
    parent_id = task.parent_event_id
    
    # On supprime la tâche
    result = task_manager.delete_task(task_id)
    
    if parent_id:
        from app.services.event_manager import EventManager
        em = EventManager.instance()
        nf_evt = em.get_event(parent_id) or em.get_event_by_external_id(parent_id, task.source)
        
        if nf_evt:
            # On retire d'abord la tâche de l'évent pour qu'il ne reste plus de référence
            em.remove_task_from_event(nf_evt.id, task_id)
            
            # Compter les autres enfants restants
            other_tasks = [t for t in task_manager.get_all_tasks() if t.get("parent_event_id") == parent_id and t["id"] != task_id]
            
            # Nettoyer l'événement si vide et créé par l'IA
            if not other_tasks and nf_evt.source == "ai_task":
                 import app.services.automation as auto
                 auto.log_auto(f"🗑️ Nettoyage de l'event IA '{nf_evt.title}' suite à la suppression de sa tâche.")
                 em.delete_event(nf_evt.id)
                 
    return {"status": "deleted"}


# === Endpoints Notifications ===

@app.get("/api/notifications")
def get_user_notifications(unread_only: bool = False):
    """Récupère les notifications de l'utilisateur."""
    return {"notifications": notif_manager.get_notifications(unread_only)}

@app.post("/api/notifications/read/{notif_id}")
def mark_notification_as_read(notif_id: str):
    """Marque une notification comme lue."""
    if notif_manager.mark_as_read(notif_id):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Notification non trouvée")

@app.post("/api/notifications/read-all")
def mark_all_notifications_as_read():
    """Marque toutes les notifications comme lues."""
    count = notif_manager.mark_all_as_read()
    return {"read_count": count}

@app.delete("/api/notifications/{notif_id}")
def delete_user_notification(notif_id: str):
    """Supprime une notification."""
    if notif_manager.delete_notification(notif_id):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Notification non trouvée")

@app.delete("/api/notifications")
def clear_user_notifications():
    """Efface toutes les notifications."""
    notif_manager.clear_all_notifications()
    return {"status": "cleared"}

# === Event Status (remis/done) ===

EVENT_STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "event_status.json")

def _load_event_status() -> dict:
    if os.path.exists(EVENT_STATUS_FILE):
        try:
            with open(EVENT_STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_event_status(data: dict):
    with open(EVENT_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.patch("/api/calendar/events/{event_id}/toggle")
def toggle_event_done(event_id: str):
    """Toggle le statut 'remis' d'un événement (ex: devoir Moodle)."""
    status = _load_event_status()
    current = status.get(event_id, False)
    status[event_id] = not current
    _save_event_status(status)
    return {"id": event_id, "done": status[event_id]}

@app.get("/api/calendar/event-status")
def get_event_status():
    """Retourne le statut de tous les événements marqués."""
    return _load_event_status()


@app.get("/api/calendar/events/simple")
async def get_simple_events():
    """Récupère une liste simplifiée des événements de tous les calendriers pour les menus déroulants."""
    from app.services.calendar_sync.aggregator import get_unified_events
    from starlette.concurrency import run_in_threadpool
    
    try:
        events = await run_in_threadpool(get_unified_events, days=30)
    except Exception as e:
        print(f"Erreur get_simple_events: {e}")
        events = []
    
    # Sort by start date, newest first or upcoming first. 
    # Let's just return them sorted by start date
    sorted_events = sorted(
        [e for e in events if e.get("start")], 
        key=lambda x: x["start"],
        reverse=True # Most recent first so upcoming/recent are at top
    )
    
    # Also include those without start date just in case
    no_date_events = [e for e in events if not e.get("start")]
    
    result = []
    for e in sorted_events[:200] + no_date_events[:50]:
         result.append({
             "id": e.get("id"),
             "external_id": e.get("external_id") or e.get("id"),
             "title": e.get("title", ""),
             "start": e.get("start", ""),
             "source": e.get("source", "unknown")
         })
         
    return {"events": result}

# === Google Calendar Events ===

@app.get("/api/calendar/events")
async def calendar_events(days: int = 30):
    """Récupère les événements unifiés (Google + Outlook + Tâches locales) pour les X prochains jours."""
    import traceback
    from app.services.calendar_sync.aggregator import get_unified_events
    from app.services.calendar_sync.microsoft_auth import MicrosoftAuthService
    
    moodle_urls = _load_moodle_urls()
    if not google_is_connected() and not MicrosoftAuthService.is_any_connected() and not moodle_urls:
        raise HTTPException(status_code=401, detail="Aucun calendrier ou lien Moodle connecté.")
    
    try:
        # Exécuter l'appel dans un threadpool pour l'agrégation
        events = await run_in_threadpool(get_unified_events, days=days)
    except Exception as e:
        print(f"💥 CRASH in get_unified_events: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur récupération calendrier: {str(e)}")
    
    # ⚡ AUTOMATION — Déclencher l'analyse IA si de nouveaux events sont détectés
    # NOTE: L'analyse se fait TOUJOURS sur la plage complète (30j), peu importe le `days` demandé par le frontend.
    # Cela évite les analyses partielles (ex: SmartFeed days=3 puis CalendarView days=30).
    try:
        existing_jobs = get_active_jobs()
        is_running = any(job["name"] == "Analyse Calendrier" for job in existing_jobs)
        
        from app.services.automation import should_trigger_periodic_sync
        
        if not is_running and (has_new_events(events) or should_trigger_periodic_sync()):
             await start_job("Analyse Calendrier", analyze_all_calendars(days=30))
    except Exception as e:
        print(f"Erreur déclenchement automation calendrier: {e}")

    
    return {"events": events, "count": len(events)}


@app.get("/api/calendar/today")
def calendar_today():
    """Récupère les événements d'aujourd'hui."""
    if not google_is_connected():
        raise HTTPException(status_code=401, detail="Google Calendar non connecté.")
    
    events = get_today_events()
    return {"events": events, "count": len(events)}



@app.post("/api/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Déclenche une synchronisation complète (Calendriers + To Do)."""
    from app.services.automation import analyze_all_calendars, sync_microsoft_todo_tasks, start_job
    
    # On lance les deux jobs
    background_tasks.add_task(start_job, "Analyse Calendrier", analyze_all_calendars)
    background_tasks.add_task(start_job, "Sync To Do", sync_microsoft_todo_tasks)
    
    return {"status": "Sync started"}

@app.post("/api/sync/todo")
async def trigger_todo_sync(background_tasks: BackgroundTasks):
    """Déclenche uniquement la synchro Microsoft To Do."""
    from app.services.automation import sync_microsoft_todo_tasks, start_job
    background_tasks.add_task(start_job, "Sync To Do", sync_microsoft_todo_tasks)
    return {"status": "To Do Sync started"}

@app.post("/api/maintenance/reset")
def maintenance_reset():
    """Réinitialise les données de l'application (Tâches, Notifications, Historique)."""
    from app.services.cleanup_utils import reset_all_data
    return {"status": "success", "results": reset_all_data()}


# === Focus Mode ===
from app.services import focus_manager

@app.post("/api/focus/start")
def start_focus(task_id: Optional[str] = None, task_title: Optional[str] = None):
    """Démarre une session de focus."""
    return focus_manager.start_focus_session(task_id, task_title)

@app.post("/api/focus/stop/{session_id}")
def stop_focus(session_id: str):
    """Termine une session de focus."""
    session = focus_manager.stop_focus_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    return session

@app.get("/api/focus/stats")
def focus_stats():
    """Récupère les statistiques de focus."""
    return focus_manager.get_focus_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
