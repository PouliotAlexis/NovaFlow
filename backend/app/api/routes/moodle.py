import os
import json
import unicodedata
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.moodle_sync_service import sync_moodle_courses, capture_moodle_token

from app.services.rag_engine.ingest import get_ingested_files
from app.core.config import settings
from app.services.automation import sync_moodle_native_v2, start_job

router = APIRouter()

from app.db.database import SessionLocal
from app.db.models import MoodleConfig

def _get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def _save_moodle_token(token: str) -> None:
    db = SessionLocal()
    try:
        config = db.query(MoodleConfig).first()
        if not config:
            config = MoodleConfig(url="https://moodle.usherbrooke.ca")
            db.add(config)
        config.token = token
        db.commit()
    finally:
        db.close()

def _save_moodle_sesskey(sesskey: str, host: str) -> None:
    db = SessionLocal()
    try:
        config = db.query(MoodleConfig).filter(MoodleConfig.url.contains(host)).first()
        if not config:
            config = MoodleConfig(url=host)
            db.add(config)
        config.sesskey = sesskey
        db.commit()
    finally:
        db.close()

def _get_moodle_token() -> Optional[str]:
    db = SessionLocal()
    try:
        config = db.query(MoodleConfig).first()
        return config.token if config else None
    finally:
        db.close()

def clean_course_name(name: str) -> str:
    """Nettoie le nom du cours pour enlever les codes techniques Moodle."""
    if not name:
        return ""
    
    name = name.strip()
    
    # Cas 1: Nom commençant par "- "
    if name.startswith("- "):
        name = name[2:].strip()
        
    # Cas 2: Format "Session-Code - Titre" (ex: A2025-BSQ111 - Développement...)
    if " - " in name:
        parts = name.split(" - ", 1)
        # Si la partie gauche contient des chiffres (souvent le cas pour les codes), on prend la partie droite
        if any(char.isdigit() for char in parts[0]):
            return parts[1].strip()
            
    return name


MOODLE_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "moodle_settings.json",
)


def _is_calendar_feed_url(url: str) -> bool:
    u = (url or "").lower()
    return (
        "export_execute.php" in u
        or "calendar/export.php" in u
        or u.endswith(".ics")
        or "authtoken=" in u
    )


def _save_calendar_url_if_feed(url: str) -> None:
    if not _is_calendar_feed_url(url):
        return

    urls = []
    if os.path.exists(MOODLE_SETTINGS_FILE):
        try:
            with open(MOODLE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                urls = data.get("urls", [])
                if not urls and data.get("url"):
                    urls = [data.get("url")]
        except Exception:
            urls = []

    clean_url = url.strip()
    if clean_url and clean_url not in urls:
        urls.append(clean_url)

    os.makedirs(os.path.dirname(MOODLE_SETTINGS_FILE), exist_ok=True)
    with open(MOODLE_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"urls": urls}, f, indent=2)

class MoodleCaptureRequest(BaseModel):
    url: str

class MoodleSyncRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    url: str

@router.post("/moodle/capture")
async def trigger_moodle_capture(request: MoodleCaptureRequest):
    """
    Lance un navigateur pour capturer le jeton Moodle SSO.
    """
    import sys
    print(f"[ROUTE] /moodle/capture appelé avec url={request.url}", flush=True)
    sys.stdout.flush()
    result = await capture_moodle_token(request.url)
    if isinstance(result, dict) and "bypass_url" in result:
        return result # Return the bypass URL to the frontend
        
    token = result
    if not token:
        raise HTTPException(status_code=408, detail="La capture du jeton a expiré ou a été annulée.")
    
    _save_moodle_token(token)
    return {"token": token}

class MoodleSessionUpdate(BaseModel):
    token: Optional[str] = None
    sesskey: Optional[str] = None
    host: Optional[str] = None

@router.post("/moodle/session/update")
async def update_moodle_session(request: MoodleSessionUpdate):
    """
    Mis à jour de la session Moodle (via extension).
    """
    import logging
    logger = logging.getLogger("moodle_api")
    
    if request.token:
        logger.info(f"✅ Reçu TOKEN via extension: {request.token[:8]}...")
        _save_moodle_token(request.token)
        return {"success": True, "type": "token"}
        
    if request.sesskey and request.host:
        logger.info(f"✅ Reçu SESSKEY via extension pour {request.host}")
        _save_moodle_sesskey(request.sesskey, request.host)
        return {"success": True, "type": "sesskey"}
        
    return {"success": False, "error": "No valid session data provided"}

@router.get("/moodle/session/status")
async def get_moodle_session_status():
    """
    Vérifie si une session Moodle est active.
    """
    db = SessionLocal()
    try:
        config = db.query(MoodleConfig).first()
        token = config.token if config else None
        sesskey = config.sesskey if config else None

        return {
            "connected": (token is not None and len(token) > 0) or (sesskey is not None and len(sesskey) > 0),
            "has_token": token is not None and len(token) > 0,
            "has_sesskey": sesskey is not None and len(sesskey) > 0
        }
    finally:
        db.close()

@router.post("/moodle/sync")
async def trigger_moodle_sync(
    request: MoodleSyncRequest, 
    background_tasks: BackgroundTasks
):
    """
    Déclenche la synchronisation des cours Moodle.
    """
    import logging
    logger = logging.getLogger("moodle_api")
    
    # Priorité : le token envoyé dans la requête (localStorage frontend)
    token = request.token or _get_moodle_token()
    
    if not token and not (request.username and request.password):
        logger.error("[SYNC] Aucun jeton ni identifiant fourni.")
        raise HTTPException(
            status_code=400, 
            detail="Session expirée. Veuillez vous reconnecter via le bouton SSO ou entrer vos identifiants."
        )

    # Sauvegarder l'URL si c'est un flux calendrier
    _save_calendar_url_if_feed(request.url)
    
    # Lancer la synchro en arrière-plan
    background_tasks.add_task(
        sync_moodle_courses,
        url=request.url,
        username=request.username,
        password=request.password,
        token=token
    )
    
    return {"status": "started", "message": "La synchronisation Moodle a été lancée en arrière-plan."}

@router.post("/moodle/sync/native")
async def trigger_native_moodle_sync(background_tasks: BackgroundTasks):
    """
    Déclenche la synchronisation Moodle.
    Si un token SSO a été capturé, utilise l'API Moodle (fiable).
    Sinon, tente le mode Playwright (peut échouer si Chrome est ouvert).
    """
    stored_token = _load_moodle_token()
    moodle_url = settings.MOODLE_URL or "https://moodle.usherbrooke.ca"
    
    if stored_token:
        # Mode fiable : utiliser le token capturé avec l'API httpx
        background_tasks.add_task(
            sync_moodle_courses,
            None,  # username
            None,  # password
            moodle_url,
            stored_token
        )
        return {"status": "started", "method": "token", "message": "Synchronisation lancée avec le token SSO."}
    else:
        # Fallback: Playwright (peut échouer)
        job_id = await start_job("Sync Moodle Native V2", sync_moodle_native_v2())
        if not job_id:
            return {"status": "already_running", "message": "Une synchronisation Moodle est déjà en cours."}
        return {"status": "started", "job_id": job_id, "message": "Synchronisation Playwright lancée (aucun token stocké)."}

@router.get("/moodle/session/status")
async def get_moodle_session_status():
    """
    Vérifie si Moodle est accessible.
    Priorité 1: Token stocké (capture SSO précédente).
    Priorité 2: Session Chrome (coûteux, peut échouer sur Windows).
    """
    # Vérifier d'abord s'il y a un token stocké
    token = _load_moodle_token()
    if token:
        return {"connected": True, "method": "token"}
    
    # Fallback: vérification via Playwright (peut échouer si Chrome est ouvert)
    try:
        from app.services.moodle_sync_service import moodle_service
        is_valid = await moodle_service.check_session_validity_cached(None)
        return {"connected": is_valid, "method": "session"}
    except Exception as e:
        return {"connected": False, "error": str(e)}

MOODLE_TOKEN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "moodle_token.json",
)

def _save_moodle_token(token: str):
    """Stocke le token Moodle capturé pour réutilisation."""
    os.makedirs(os.path.dirname(MOODLE_TOKEN_FILE), exist_ok=True)
    import datetime
    with open(MOODLE_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"token": token, "captured_at": datetime.datetime.now().isoformat()}, f)

def _load_moodle_token() -> str | None:
    """Charge le dernier token Moodle capturé."""
    if os.path.exists(MOODLE_TOKEN_FILE):
        try:
            with open(MOODLE_TOKEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("token")
        except Exception:
            pass
    return None

class MoodleLoginRequest(BaseModel):
    token: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

@router.post("/moodle/login")
async def trigger_moodle_login(request: MoodleLoginRequest):
    """
    Ouvre un navigateur distant via Browserless pour capturer le token Moodle SSO Microsoft.
    Si un token est fourni directement par le client, on le sauvegarde.
    """
    import logging
    logger = logging.getLogger("moodle_api")
    
    if request.token:
        logger.info(f"[LOGIN] Utilisation du token fourni par le client.")
        _save_moodle_token(request.token)
        return {"success": True, "message": "Token client enregistré."}
    
    if not request.email or not request.password:
        return {"success": False, "error": "Email et mot de passe requis pour le SSO automatique."}
        
    try:
        logger.info(f"[LOGIN] Lancement Browserless pour {request.email}...")
        
        from app.services.moodle_scraper import get_moodle_session_via_browserless
        result = await get_moodle_session_via_browserless(request.email, request.password)
        
        if result.get("success") and result.get("token"):
            _save_moodle_token(result["token"])
            logger.info(f"[LOGIN] Token Moodle capturé avec succès (Browserless)!")
            return {"success": True, "message": "Connexion réussie ! Token capturé.", "token": result["token"]}
        else:
            logger.warning(f"[LOGIN] Échec Browserless: {result.get('error')}")
            return {"success": False, "error": result.get("error", "Erreur inconnue.")}

    except Exception as e:
        import traceback
        logger.error(f"[LOGIN] CRASH: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}

@router.get("/moodle/courses")
async def list_moodle_courses():
    """
    Liste les cours synchronisés localement.
    """
    dest_dir = settings.MOODLE_DOWNLOADS_DESTINATION
    if not os.path.exists(dest_dir):
        return []
        
    courses = []
    # Chaque dossier dans dest_dir est un CID (Course ID)
    for cid in os.listdir(dest_dir):
        course_path = os.path.join(dest_dir, cid)
        if os.path.isdir(course_path):
            files = []
            ALLOWED_EXT = (".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".jpg", ".jpeg", ".png", ".gif", ".svg")
            for root, dirs, filenames in os.walk(course_path):
                files += [f for f in filenames if f.lower().endswith(ALLOWED_EXT)]


            
            # Tenter de lire le nom du cours depuis course_info.json
            name = f"Cours {cid}"
            info_path = os.path.join(course_path, "course_info.json")
            if os.path.exists(info_path):
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        name = clean_course_name(info.get("name", name))

                except Exception:
                    pass
                    
            courses.append({
                "id": cid,
                "name": name,
                "filesCount": len(files)
            })
            
    return courses

@router.get("/moodle/courses/{course_id}")
async def get_course_details(course_id: str):
    """
    Récupère les détails d'un cours spécifique.
    """
    dest_dir = settings.MOODLE_DOWNLOADS_DESTINATION
    course_path = os.path.join(dest_dir, course_id)
    
    if not os.path.exists(course_path) or not os.path.isdir(course_path):
        raise HTTPException(status_code=404, detail="Cours non trouvé")
        
    # Tenter de lire le nom du cours depuis course_info.json
    name = f"Cours {course_id}"
    info_path = os.path.join(course_path, "course_info.json")
    if os.path.exists(info_path):
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
                name = clean_course_name(info.get("name", name))

        except Exception:
            pass
            
    return {
        "id": course_id,
        "name": name,
        "path": course_path
    }

@router.get("/moodle/courses/{course_id}/files")
async def list_course_files(course_id: str):
    """
    Liste les fichiers d'un cours spécifique et leur état d'ingestion.
    """
    dest_dir = settings.MOODLE_DOWNLOADS_DESTINATION
    course_path = os.path.join(dest_dir, course_id)
    
    if not os.path.exists(course_path) or not os.path.isdir(course_path):
        return []
        
    # Récupérer les fichiers injectés dans ChromaDB pour ce cours
    ingested_files = get_ingested_files(course_id)
    
    files_list = []
    ALLOWED_EXT = (".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".jpg", ".jpeg", ".png", ".gif", ".svg")
    for root, dirs, filenames in os.walk(course_path):
        for f in filenames:
            # On ne liste que les types supportés par le scraper
            if f.lower().endswith(ALLOWED_EXT):

                # On normalise en NFC pour la comparaison avec Chroma
                f_norm = unicodedata.normalize('NFC', f)
                is_ingested = f_norm in ingested_files

                
                files_list.append({
                    "name": f,
                    "ingested": is_ingested,
                    "size": os.path.getsize(os.path.join(root, f)),
                    "path": os.path.relpath(os.path.join(root, f), course_path)
                })
                
    return files_list

@router.get("/moodle/courses/{course_id}/files/{filename:path}")
async def get_course_file(course_id: str, filename: str):
    """
    Sert le contenu d'un fichier de cours spécifique.
    """
    dest_dir = settings.MOODLE_DOWNLOADS_DESTINATION
    file_path = os.path.normpath(os.path.join(dest_dir, course_id, filename))
    
    # Sécurité : vérifier que le chemin est bien dans le dossier de destination
    if not file_path.startswith(os.path.normpath(dest_dir)):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
        
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
        
    return FileResponse(file_path)
