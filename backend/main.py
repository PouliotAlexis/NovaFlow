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
from services.google_calendar import (
    get_auth_url,
    handle_callback,
    is_connected as google_is_connected,
    disconnect as google_disconnect,
    get_upcoming_events,
    get_today_events,
)
from services.task_manager import get_tasks, add_task, update_task, delete_task, toggle_task
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

# === App Setup ===

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="NovaFlow - Votre Life OS intelligent et privé.",
)

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

@app.get("/api/auth/google")
def google_auth():
    """Démarre le flow OAuth Google Calendar."""
    try:
        auth_url = get_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur OAuth: {str(e)}")


@app.get("/api/auth/google/callback")
def google_callback(code: str):
    """
    Callback OAuth Google.
    Google redirige ici après l'autorisation.
    """
    try:
        result = handle_callback(code)
        # Rediriger vers le frontend avec un message de succès
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="http://localhost:3000?google_connected=true")
    except Exception as e:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"http://localhost:3000?google_error={str(e)}")


@app.get("/api/auth/google/status")
def google_status():
    """Vérifie si Google Calendar est connecté."""
    return {"connected": google_is_connected()}

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


@app.delete("/api/auth/google")
def google_logout():
    """Déconnecte Google Calendar."""
    google_disconnect()
    return {"status": "disconnected"}


# === Endpoints Tâches ===

@app.get("/api/tasks")
def get_all_tasks():
    """Récupère toutes les tâches."""
    return get_tasks()

@app.post("/api/tasks")
def create_new_task(task: TaskRequest):
    """Crée une nouvelle tâche."""
    return add_task(task.title, priority="medium", meta="Utilisateur")

@app.patch("/api/tasks/{task_id}/toggle")
def toggle_task_status(task_id: str):
    """Inverse le statut d'une tâche."""
    result = toggle_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    return result

@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: str):
    """Supprime une tâche."""
    result = delete_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    return {"status": "deleted"}


# === Google Calendar Events ===

@app.get("/api/calendar/events")
async def calendar_events(days: int = 7):
    """Récupère les événements des X prochains jours."""
    if not google_is_connected():
        raise HTTPException(status_code=401, detail="Google Calendar non connecté.")
    
    # Exécuter l'appel synchrone dans un threadpool pour ne pas bloquer la boucle async
    events = await run_in_threadpool(get_upcoming_events, days=days)
    
    # ⚡ AUTOMATION: Analyser les événements (Job Tracké)
    try:
        # Debug: Vérifier si une loop existe
        try:
            loop = asyncio.get_running_loop()
        except Exception as e:
            print(f"DEBUG Loop Error: {e}")

        # DEDUPLICATION: Vérifier si un job "Analyse Calendrier" tourne déjà
        existing_jobs = get_active_jobs()
        is_running = any(job["name"] == "Analyse Calendrier" for job in existing_jobs)
        
        if is_running:
            # print("ℹ️ Auto: Analyse Calendrier déjà en cours, on ignore.")
            pass
        elif has_new_events(events):
            start_job("Analyse Calendrier", analyze_calendar_for_tasks(events))
        else:
            # print("ℹ️ Auto: Rien de nouveau dans le calendrier.")
            pass

    except Exception as e:
        print(f"ERREUR CRITIQUE START_JOB: {e}")
        # On ne raise PAS d'erreur pour ne pas bloquer l'affichage du calendrier

    
    return {"events": events, "count": len(events)}


@app.get("/api/calendar/today")
def calendar_today():
    """Récupère les événements d'aujourd'hui."""
    if not google_is_connected():
        raise HTTPException(status_code=401, detail="Google Calendar non connecté.")
    
    events = get_today_events()
    return {"events": events, "count": len(events)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
