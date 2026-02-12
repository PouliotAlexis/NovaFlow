"""
NovaFlow API - Point d'entrée principal

Ce fichier définit toutes les routes de l'API FastAPI.
"""

import sys
import os
import shutil

# Ajouter le dossier backend au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
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

# === App Setup ===

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="NovaFlow - Votre Life OS intelligent et privé.",
)

# CORS - Permettre au Frontend Next.js de communiquer avec le Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
    ],
    allow_credentials=True,
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

    # Recherche de contexte RAG dans les documents
    if request.use_rag:
        context = get_relevant_context(prompt, n_results=5)

    # Si mode Cloud, sanitizer le message AVANT l'envoi
    if active_mode == "cloud":
        prompt, san_map = sanitize(prompt, request.sensitive_entities)
        if context:
            context, _ = sanitize(context)  # Sanitizer aussi le contexte
        was_sanitized = True

        # Récupération events Google Calendar (si connecté)
    if google_is_connected():
        try:
            events = get_upcoming_events(days=30, max_results=50)
            if events:
                cal_ctx = "\n\n## Mon Calendrier (30 prochains jours)\n"
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


# === Endpoints Documents (RAG) ===

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
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


@app.delete("/api/auth/google")
def google_logout():
    """Déconnecte Google Calendar."""
    google_disconnect()
    return {"status": "disconnected"}


# === Google Calendar Events ===

@app.get("/api/calendar/events")
def calendar_events(days: int = 7):
    """Récupère les événements des X prochains jours."""
    if not google_is_connected():
        raise HTTPException(status_code=401, detail="Google Calendar non connecté.")
    
    events = get_upcoming_events(days=days)
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
