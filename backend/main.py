"""
NovaFlow API - Point d'entrée principal

Ce fichier définit toutes les routes de l'API FastAPI.
"""

import sys
import os
import shutil
from datetime import datetime
import asyncio
import os
import json

# Ajouter le dossier backend au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, List

from core.config import settings
from services.sanitizer import sanitize, desanitize, SanitizationMap
from services.ai_engine import chat
from services.document_processor import (
    ingest_document,
    get_relevant_context,
    list_documents,
    delete_document,
    UPLOADS_DIR,
)
from services.google_service import (
    get_auth_url,
    handle_callback,
    is_any_connected as google_is_connected,
    disconnect_account as google_disconnect,
    get_upcoming_events,
    get_today_events,
    list_connected_accounts
)
from services.task_manager import TaskManager, NovaFlowTask
import re
from services.automation import (
    analyze_document_for_tasks, 
    analyze_calendar_for_tasks, 
    get_recent_logs,
    start_job,
    cancel_job,
    get_active_jobs,
    has_new_events
)
from services.chat_manager import load_chat_history, save_chat_message, clear_chat_history
from services.notification_manager import NotificationManager

# === App Setup ===

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="NovaFlow - Votre Life OS intelligent et privé.",
)

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
        tasks_to_create = re.findall(task_pattern, ai_response)
        
        for task_title in tasks_to_create:
            print(f"✨ AI Action: Creating task '{task_title}'")
            add_task(title=task_title, priority="medium", meta="AI Generated")
            # Remplacer la commande par une confirmation visible
            ai_response = ai_response.replace(f"[TASK: {task_title}]", f"✅ Tâche '{task_title}' ajoutée.")

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
        start_job(
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


@app.get("/api/auth/google/accounts")
def google_accounts_list():
    """Liste les comptes Google connectés."""
    return {"accounts": list_connected_accounts()}

@app.get("/api/auth/google/disconnect")
def google_disconnect_all():
    """Déconnecte TOUS les comptes Google (pour compatibilité)."""
    accounts = list_connected_accounts()
    for acc in accounts:
        google_disconnect(acc)
    return {"status": "all_disconnected"}

# === Endpoints Automation ===

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
def get_all_tasks():
    """Récupère toutes les tâches."""
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

@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: str):
    """Supprime une tâche."""
    result = task_manager.delete_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
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


# === Google Calendar Events ===

@app.get("/api/calendar/events")
async def calendar_events(days: int = 30):
    """Récupère les événements unifiés (Google + Tâches locales) pour les X prochains jours."""
    from services.calendar_aggregator import get_unified_events
    
    if not google_is_connected():
        raise HTTPException(status_code=401, detail="Google Calendar non connecté.")
    
    # Exécuter l'appel dans un threadpool pour l'agrégation
    events = await run_in_threadpool(get_unified_events, days=days)
    
    # ⚡ AUTOMATION — Déclencher l'analyse IA si de nouveaux events sont détectés
    # NOTE: L'analyse se fait TOUJOURS sur la plage complète (30j), peu importe le `days` demandé par le frontend.
    # Cela évite les analyses partielles (ex: SmartFeed days=3 puis CalendarView days=30).
    try:
        existing_jobs = get_active_jobs()
        is_running = any(job["name"] == "Analyse Calendrier" for job in existing_jobs)
        if not is_running and has_new_events(events):
             start_job("Analyse Calendrier", analyze_calendar_for_tasks(events=None, days=30))
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


@app.post("/api/maintenance/reset")
def maintenance_reset():
    """Réinitialise les données de l'application (Tâches, Notifications, Historique)."""
    from services.cleanup_utils import reset_all_data
    return {"status": "success", "results": reset_all_data()}


# === Focus Mode ===
from services import focus_manager

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
