import os
import json
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.moodle_service import sync_moodle_courses
from app.services.moodle_browser import capture_moodle_token
from app.services.rag_engine.ingest import get_ingested_files
from app.core.config import settings
from app.services.automation import sync_moodle_native_v2, start_job

router = APIRouter()

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
    token = await capture_moodle_token(request.url)
    if not token:
        raise HTTPException(status_code=408, detail="La capture du jeton a expiré ou a été annulée.")
    return {"token": token}

@router.post("/moodle/sync")
async def trigger_moodle_sync(
    request: MoodleSyncRequest, 
    background_tasks: BackgroundTasks
):
    """
    Déclenche la synchronisation Moodle en arrière-plan.
    """
    if not request.token and (not request.username or not request.password):
        raise HTTPException(status_code=400, detail="Vous devez fournir soit des identifiants (CIP/Pass), soit un jeton (Token).")

    # Si l'URL fournie est un flux calendrier Moodle (iCal/RSS),
    # on l'ajoute aux réglages pour qu'il soit visible dans /api/calendar/events.
    _save_calendar_url_if_feed(request.url)

    background_tasks.add_task(
        sync_moodle_courses, 
        request.username, 
        request.password, 
        request.url,
        request.token
    )
    
    return {"status": "started", "message": "La synchronisation Moodle a été lancée en arrière-plan."}

@router.post("/moodle/sync/native")
async def trigger_native_moodle_sync():
    """
    Déclenche la nouvelle synchronisation native (Playwright) via le job d'automatisation.
    """
    job_id = await start_job("Sync Moodle Native V2", sync_moodle_native_v2())
    if not job_id:
        return {"status": "already_running", "message": "Une synchronisation Moodle est déjà en cours."}
    
    return {"status": "started", "job_id": job_id, "message": "Synchronisation native lancée."}

@router.get("/moodle/session/status")
async def get_moodle_session_status():
    """
    Vérifie si la session Chrome permet d'accéder à Moodle (version cachée).
    """
    from app.services.moodle_sync_service import moodle_service
    
    try:
        is_valid = await moodle_service.check_session_validity_cached(None)
        return {"connected": is_valid}
    except Exception as e:
        return {"connected": False, "error": str(e)}

@router.post("/moodle/login")
async def trigger_moodle_login():
    """
    Ouvre une fenêtre Chrome pour que l'utilisateur se connecte manuellement.
    """
    from app.services.moodle_sync_service import moodle_service
    import traceback
    import logging
    
    logger = logging.getLogger("moodle_api")
    try:
        logger.info("[LOGIN] Déclenchement connexion interactive...")
        result = await moodle_service.login_interactively()
        logger.info(f"[LOGIN] Résultat: {result}")
        
        if isinstance(result, dict):
            return result
        
        return {
            "success": result, 
            "message": "Connexion réussie" if result else "Échec de la connexion"
        }
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"[LOGIN] CRASH: {e}\n{error_trace}")
        return {"success": False, "error": str(e), "trace": error_trace}

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
            for root, dirs, filenames in os.walk(course_path):
                files += [f for f in filenames if f.endswith(".pdf")]
            
            # Tenter de lire le nom du cours depuis course_info.json
            name = f"Cours {cid}"
            info_path = os.path.join(course_path, "course_info.json")
            if os.path.exists(info_path):
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        name = info.get("name", name)
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
                name = info.get("name", name)
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
    for root, dirs, filenames in os.walk(course_path):
        for f in filenames:
            # On ne liste que les types supportés par l'ingestion
            if f.endswith((".pdf", ".txt", ".md")):
                # On compare le nom du fichier (puisque ingest.py stocke le basename dans Chroma source si on compare ainsi)
                is_ingested = f in ingested_files
                
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
