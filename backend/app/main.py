import sys
import asyncio

# Fix pour Windows : Nécessaire pour Playwright (sous-processus)
# DOIT ÊTRE APPELÉ AVANT TOUT AUTRE IMPORT OU CRÉATION DE LOOP
if sys.platform == "win32":
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("[WINDOWS FIX] ProactorEventLoopPolicy appliqué avec succès.")
    except Exception as e:
        print(f"[WINDOWS FIX] Erreur lors de l'application de la politique: {e}")

import os
# NovaFlow v0.1.2 - Force Reload Final
import shutil
from datetime import datetime
import traceback
import json


from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, List

from app.core.config import settings
from app.services.sanitizer import sanitize, desanitize, SanitizationMap
from app.services.ai_engine import chat, chat_stream
from app.services.rag_engine.ingest import (
    ingest_document,
    query_rag,
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
from app.services.context_builder import ContextBuilder
from app.services.cloud_storage import CloudStorageService
from app.db.database import SessionLocal
from app.api.routes import auth as auth_router
from app.api.routes import chat as chat_router
from app.api.routes import moodle as moodle_router
from app.services.auth_service import get_current_user
from app.db.models import User # Pour les indexation futures

# === App Setup & Database Initialization ===

from app.db.database import engine, SessionLocal
from app.db.models import Base, MoodleConfig
# Création automatique des tables (Similaire à une migration légère)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="NovaFlow - Votre Life OS intelligent et privé.",
)

# CORS au Sommet pour tout intercepter
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://nova-flow-mu.vercel.app",
        "https://nova-flow-mu.vercel.app/",
        "http://nova-flow-mu.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def cors_debug_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin:
        print(f"[CORS DEBUG] Request from Origin: {origin} for {request.method} {request.url.path}")
    response = await call_next(request)
    return response

# Inclusion des nouveaux routers
app.include_router(chat_router.router, prefix="/api/v2", tags=["Chat V2"])
app.include_router(moodle_router.router, prefix="/api/v2", tags=["Moodle V2"])
app.include_router(auth_router.router)

# Managers Instances
task_manager = TaskManager.instance()
notif_manager = NotificationManager.instance()

# Exception handler pour s'assurer que les erreurs ont aussi les headers CORS
from fastapi.responses import JSONResponse
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    # Les middlewares s'occuperont d'ajouter les headers CORS si on utilise dispatch
    return response

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    error_msg = f"[ERROR] Global exception: {exc}\n{traceback.format_exc()}"
    print(error_msg)
    with open("backend_crash.log", "a", encoding="utf-8") as f:
        f.write(f"--- {datetime.now()} ---\n{error_msg}\n")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "msg": str(exc)},
    )

# Handlers déjà définis au sommet


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

@app.get("/api/ping")
def ping_auth(current_user: User = Depends(get_current_user)):
    return {"status": "ok", "user": current_user.email}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    Endpoint principal de chat avec l'IA.
    """
    active_mode = request.mode or current_user.ai_mode or settings.AI_MODE
    was_sanitized = False
    san_map = None
    context = ""

    prompt = request.message
    
    # Sauvegarder le message utilisateur dans l'historique
    save_chat_message("user", prompt, user_id=current_user.id)

    # Utilisation du ContextBuilder pour aggréger Tâches + Calendrier + RAG
    context = ContextBuilder.build_global_context(
        user_query=prompt,
        include_tasks=True,
        include_calendar=True,
        user_id=current_user.id
    )

    # RAG additionnel si demandé
    if request.use_rag:
        try:
            rag_ctx = get_relevant_context(prompt, n_results=5)
            if rag_ctx:
                context += f"\n\n## Contexte Documentaire\n{rag_ctx}"
        except Exception:
            pass

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

        # Remplacement robuste via regex
        def create_and_confirm_task(match):
            task_title = match.group(1).strip()
            print(f"✨ AI Action: Creating task '{task_title}' (Course: {course_id})")
            
            # Créer la tâche
            task_manager.add_task(
                title=task_title, 
                priority="medium", 
                meta=f"AI Generated ({course_id or 'Global'})",
                course_id=course_id
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
        save_chat_message("ai", ai_response, user_id=current_user.id)

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
async def chat_stream_endpoint(
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint de chat avec réponse en streaming (Server-Sent Events).
    """
    active_mode = request.mode or current_user.ai_mode or settings.AI_MODE
    was_sanitized = False
    san_map = None
    context = ""
    prompt = request.message

    # Utilisation du Sanitizer si activé
    was_sanitized = False
    san_map = None
    if current_user.privacy_mode:
        prompt, san_map = sanitize(prompt)
        was_sanitized = True
        print(f"🛡️ Privacy Mode: Prompt sanitized (Mapping size: {len(san_map)})")

    # Utilisation du ContextBuilder (Streaming)
    context = ContextBuilder.build_global_context(
        user_query=prompt,
        include_tasks=True,
        include_calendar=True,
        user_id=current_user.id
    )

    if request.use_rag:
        try:
            rag_ctx = get_relevant_context(prompt, n_results=5)
            if rag_ctx:
                context += f"\n\n## Contexte Documentaire\n{rag_ctx}"
        except Exception:
            pass

    save_chat_message("user", prompt if not was_sanitized else request.message, user_id=current_user.id)

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

        except asyncio.CancelledError:
            print("[CHAT] Stream cancelled by client.")
            return
        except Exception as e:
            err_trace = traceback.format_exc()
            print(f"💥 CHAT STREAM ERROR: {e}\n{err_trace}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'traceback': err_trace})}\n\n"
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

        # Remplacement robuste via regex
        def create_and_confirm_task_stream(match):
            task_title = match.group(1).strip()
            print(f"✨ AI Stream Action: Creating task '{task_title}' (Course: {course_id})")
            
            # Créer la tâche
            task_manager.add_task(
                title=task_title, 
                priority="medium", 
                meta=f"AI Generated ({course_id or 'Global'})",
                course_id=course_id
            )
            
            # Envoyer une notification pour feedback immédiat
            notif_manager.add_notification(
                title="Nouvelle tâche",
                content=f"L'IA a créé la tâche : {task_title}" + (f" (Cours: {course_id})" if course_id else ""),
                type="success"
            )
            
            return f"✅ Tâche '{task_title}' ajoutée."

        processed = re.sub(task_pattern, create_and_confirm_task_stream, processed, flags=re.IGNORECASE)
        
        # Sauvegarde garantie via BackgroundTasks pour éviter les interruptions client
        def task_save():
            log_path = os.path.join(settings.BASE_DIR, "db_audit.log")
            try:
                save_chat_message("ai", processed, user_id=current_user.id)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] SUCCESS: AI message saved for user_id={current_user.id}\n")
            except Exception as e:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] ERROR: AI message save failed for user_id={current_user.id}: {e}\n")

        background_tasks.add_task(task_save)

        yield f"data: {json.dumps({'type': 'done', 'response': processed, 'mode_used': active_mode, 'context_used': bool(context)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "identity",
        },
    )


# === Endpoints Chat History ===

@app.get("/api/chat/history")
def get_chat_history(current_user: User = Depends(get_current_user)):
    """Récupère l'historique des conversations de l'utilisateur."""
    from app.services.chat_manager import load_chat_history
    return {"history": load_chat_history(user_id=current_user.id)}

@app.delete("/api/chat/history")
def delete_chat_history(current_user: User = Depends(get_current_user)):
    """Efface l'historique des conversations."""
    print(f"[CHAT DEBUG] Request: Delete history for user: {current_user.id} ({current_user.email})")
    count = clear_chat_history(user_id=current_user.id)
    return {"status": "cleared", "deleted_count": count}


# === Endpoints Documents (RAG) ===

@app.post("/api/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
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
    result = ingest_document(file_path) # Utilise le nom du fichier par défaut
    
    # ⚡ CLOUD SYNC: Enregistrer et uploader vers Google Drive
    db = SessionLocal()
    try:
        CloudStorageService.register_and_upload(file_path, db)
        # Assigner à l'utilisateur
        from app.db.models import CloudFile
        cloud_file = db.query(CloudFile).filter(CloudFile.id == file.filename).first()
        if cloud_file:
            cloud_file.user_id = current_user.id
            db.commit()
    finally:
        db.close()

    # Correction pour que le résultat contienne ce que l'automation attend
    if result["status"] == "success":
        result["status"] = "analyzed"
    
    # ⚡ AUTOMATION: Lancer l'analyse en tant que Job tracké
    if result["status"] == "analyzed":
        await start_job(
            f"Analyse doc: {result['file_name']}",
            analyze_document_for_tasks(
                doc_id=result["file_name"], # On utilise le nom comme ID stable
                file_name=result["file_name"]
            )
        )
    
    return result


@app.get("/api/documents")
def get_documents(current_user: User = Depends(get_current_user)):
    """Liste tous les documents de l'utilisateur."""
    # Note: list_documents() actuel est global, on devrait le filtrer par la DB
    db = SessionLocal()
    try:
        from app.db.models import CloudFile
        docs = db.query(CloudFile).filter(CloudFile.user_id == current_user.id).all()
        # Fallback pour les fichiers déjà là
        if not docs:
             docs = db.query(CloudFile).filter(CloudFile.user_id == None).all()
        return {"documents": docs}
    finally:
        db.close()

@app.delete("/api/documents/{doc_id}")
def remove_document(doc_id: str, current_user: User = Depends(get_current_user)):
    """Supprime un document (vérifie d'abord l'appartenance)."""
    db = SessionLocal()
    try:
        from app.db.models import CloudFile
        doc = db.query(CloudFile).filter(CloudFile.id == doc_id, CloudFile.user_id == current_user.id).first()
        if not doc:
             # Fallback migration
             doc = db.query(CloudFile).filter(CloudFile.id == doc_id, CloudFile.user_id == None).first()
        
        if not doc:
             raise HTTPException(status_code=404, detail="Document non trouvé ou accès refusé.")
             
        success = delete_document(doc_id)
        if success:
            db.delete(doc)
            db.commit()
            return {"status": "deleted", "doc_id": doc_id}
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression vectorielle.")
    finally:
        db.close()


@app.get("/api/documents/{doc_id}/download")
def download_document(doc_id: str):
    """Télécharge/ouvre un document uploadé."""
    docs = list_documents()
    doc = next((d for d in docs if d["doc_id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé.")
    
    file_path = os.path.join(UPLOADS_DIR, doc["file_name"])
    
    # ⚡ CLOUD SYNC: S'assurer que le fichier est disponible localement (Multi-Device)
    db = SessionLocal()
    try:
        if not os.path.exists(file_path):
            success = CloudStorageService.ensure_local_copy(doc["file_name"], file_path, db)
            if not success:
                 raise HTTPException(status_code=404, detail="Fichier non trouvé localement et échec du téléchargement Cloud.")
    finally:
        db.close()
    
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


# === Moodle Settings (DB Version) ===

def _load_moodle_urls() -> list:
    """Charge les URLs Moodle depuis la base de données."""
    with SessionLocal() as db:
        configs = db.query(MoodleConfig).filter(MoodleConfig.is_active == True).all()
        return [c.url for c in configs]

def _save_moodle_urls(urls: list):
    """Met à jour les URLs Moodle en base de données."""
    with SessionLocal() as db:
        # On désactive les anciennes URLs non présentes dans la nouvelle liste
        db.query(MoodleConfig).filter(MoodleConfig.url.notin_(urls)).update({"is_active": False}, synchronize_session=False)
        
        for url in urls:
            existing = db.query(MoodleConfig).filter(MoodleConfig.url == url).first()
            if existing:
                existing.is_active = True
            else:
                db.add(MoodleConfig(url=url, is_active=True))
        db.commit()

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
import traceback

@app.get("/api/auth/google/login")
def google_login():
    """Retourne l'URL de connexion Google."""
    try:
        url = get_auth_url()
        return {"url": url}
    except Exception as e:
        print(f"❌ Error generating Google auth URL: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/google/callback")
def google_callback(code: str, state: Optional[str] = None):
    """Callback OAuth Google - retourne une page HTML de succès."""
    from fastapi.responses import HTMLResponse
    try:
        result = handle_callback(code, state=state)
        if result.get("status") == "connected":
           email = result.get("message", "").split(" ")[1] # Récupère l'email s'il est dans le format standard
           html = f"""
           <html><body style="background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif">
               <div style="text-align:center">
                   <h2 style="color: #4285F4">✅ Google connected!</h2>
                   <p>Account linked successfully.</p>
                   <p style="color:#888">You can close this window.</p>
               </div>
               <script>setTimeout(() => window.close(), 1500);</script>
           </body></html>
           """
           return HTMLResponse(content=html)
        else:
           return JSONResponse(status_code=400, content=result)
    except Exception as e:
        print(f"❌ Error in Google callback: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


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
def get_all_tasks(current_user: User = Depends(get_current_user)):
    from app.services.task_manager import TaskManager
    tm = TaskManager.instance()
    # Utiliser directly from_db pour garantir que TOUS les champs (id, course_id, etc.) sont présents
    return tm.get_all_tasks(user_id=current_user.id)

@app.post("/api/tasks")
def create_new_task(task: TaskRequest, current_user = Depends(get_current_user)):
    """Crée une nouvelle tâche pour l'utilisateur actuel."""
    return task_manager.add_task(task.title, priority="medium", meta="Utilisateur", user_id=current_user.id)

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
async def get_simple_events(current_user: User = Depends(get_current_user)):
    """Récupère une liste simplifiée des événements pour les menus déroulants."""
    from app.services.calendar_sync.aggregator import get_unified_events, get_moodle_events, get_moodle_extension_events
    from starlette.concurrency import run_in_threadpool
    
    try:
        events = await run_in_threadpool(get_unified_events, days=30, user_id=current_user.id)
    except Exception as e:
        print(f"Erreur get_simple_events: {e}")
    
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

from fastapi.responses import JSONResponse # Added for the new calendar_events endpoint

@app.get("/api/calendar/events")
def calendar_events(days: int = 30, current_user: User = Depends(get_current_user)):
    """Récupère les événements unifiés pour l'utilisateur actuel."""
    import traceback
    from app.services.calendar_sync.aggregator import get_unified_events
    try:
        events = get_unified_events(days=days, user_id=current_user.id)
        return {"events": events, "count": len(events)}
    except Exception as e:
        err_detail = traceback.format_exc()
        print(f"💥 CRASH in calendar_events: {e}\n{err_detail}")
        return JSONResponse(
            status_code=500, 
            content={
                "detail": f"Erreur récupération calendrier: {str(e)}",
                "traceback": err_detail
            }
        )


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
    # En production, on utilise le PORT fourni par l'environnement
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
