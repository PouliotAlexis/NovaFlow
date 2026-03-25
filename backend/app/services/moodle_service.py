import os
import httpx
import asyncio
from typing import List, Dict, Any
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
from app.services.rag_engine.ingest import ingest_document
from app.core.config import settings

from .moodle_utils import normalize_moodle_url

class MoodleService:
    def __init__(self, base_url: str, username: str = None, password: str = None, token: str = None):
        self.base_url = normalize_moodle_url(base_url)
        self.username = username
        self.password = password
        self.token = token
        self.client = httpx.AsyncClient(timeout=30.0)

    async def authenticate(self) -> str:
        """Obtient un token d'authentification Moodle Mobile API."""
        if self.token:
            return self.token
        
        login_url = f"{self.base_url}/login/token.php"
        params = {
            "username": self.username,
            "password": self.password,
            "service": "moodle_mobile_app"
        }
        
        response = await self.client.post(login_url, params=params)
        data = response.json()
        
        if "token" in data:
            self.token = data["token"]
            return self.token
        else:
            raise Exception(f"Erreur d'authentification Moodle : {data.get('error', 'Inconnue')}")

    async def call_web_service(self, function_name: str, params: Dict[str, Any] = None) -> Any:
        """Appelle un service web Moodle."""
        if not self.token:
            await self.authenticate()
        
        url = f"{self.base_url}/webservice/rest/server.php"
        default_params = {
            "wstoken": self.token,
            "wsfunction": function_name,
            "moodlewsrestformat": "json"
        }
        if params:
            default_params.update(params)
        
        response = await self.client.get(url, params=default_params)
        return response.json()

    async def get_courses(self, user_id: int):
        """Récupère la liste des cours de l'utilisateur."""
        return await self.call_web_service("core_enrol_get_users_courses", {"userid": user_id})

    async def get_course_contents(self, course_id: int):
        """Récupère le contenu d'un cours."""
        return await self.call_web_service("core_course_get_contents", {"courseid": course_id})

    def _prepare_download_url(self, file_url: str) -> str:
        """Ajoute le token à l'URL de téléchargement."""
        parts = list(urlparse(file_url))
        query = dict(parse_qsl(parts[4]))
        query.update({"token": self.token})
        parts[4] = urlencode(query)
        return urlunparse(parts)

    async def download_file(self, file_url: str, dest_dir: str, file_name: str) -> str:
        """Télécharge un fichier dans le dossier de destination."""
        dl_url = self._prepare_download_url(file_url)
        dest_path = os.path.join(dest_dir, file_name)
        
        os.makedirs(dest_dir, exist_ok=True)
        
        async with self.client.stream("GET", dl_url) as response:
            if response.status_code == 200:
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                return dest_path
            else:
                raise Exception(f"Erreur téléchargement ({response.status_code}) : {file_url}")

async def sync_moodle_courses(username, password, url, token=None):
    """
    Fonction wrapper pour synchroniser les cours Moodle.
    """
    import traceback
    print(f"[MOODLE SYNC] Démarrage sync: url={url}, token={'oui' if token else 'non'}", flush=True)

    service = MoodleService(url, username, password, token)
    await service.authenticate()
    print(f"[MOODLE SYNC] Authentification OK, token={service.token[:8]}...", flush=True)
    
    # Get user info for ID
    user_info = await service.call_web_service("core_webservice_get_site_info")
    user_id = user_info.get("userid")
    print(f"[MOODLE SYNC] user_id={user_id}", flush=True)
    
    courses = await service.get_courses(user_id)
    print(f"[MOODLE SYNC] {len(courses)} cours trouvés", flush=True)
    download_dir = settings.MOODLE_DOWNLOADS_DESTINATION
    
    results = []
    for course in courses:
        course_name = course.get("fullname", "Unknown Course")
        course_id = course.get("id")
        course_dir = os.path.join(download_dir, str(course_id))
        os.makedirs(course_dir, exist_ok=True)
        print(f"[MOODLE SYNC] Cours: {course_name} (id={course_id})", flush=True)
        
        # Sauvegarder les infos du cours pour le dashboard
        with open(os.path.join(course_dir, "course_info.json"), "w", encoding="utf-8") as f:
            import json
            json.dump({"id": course_id, "name": course_name}, f, ensure_ascii=False, indent=2)
        
        contents = await service.get_course_contents(course_id)
        pdf_count = 0
        for section in contents:
            for module in section.get("modules", []):
                modname = module.get("modname")
                for content in module.get("contents", []):
                    if content.get("type") == "file" and content.get("filename", "").endswith(".pdf"):
                        pdf_count += 1
                        file_url = content.get("fileurl")
                        file_name = content.get("filename")
                        print(f"[MOODLE SYNC]   PDF trouvé ({modname}): {file_name}", flush=True)
                        
                        # Téléchargement
                        try:
                            file_path = await service.download_file(file_url, course_dir, file_name)
                            print(f"[MOODLE SYNC]   Téléchargé: {file_path}", flush=True)
                            # Ingestion RAG
                            ingest_result = ingest_document(file_path, course_id=str(course_id))
                            results.append({
                                "course": course_name,
                                "file": file_name,
                                "status": "synced",
                                "rag": ingest_result
                            })
                        except Exception as e:
                            print(f"[MOODLE SYNC]   ERREUR {file_name}: {e}", flush=True)
                            traceback.print_exc()
                            results.append({
                                "course": course_name,
                                "file": file_name,
                                "status": "error",
                                "error": str(e)
                            })
        print(f"[MOODLE SYNC]   → {pdf_count} PDF(s) dans ce cours", flush=True)
    
    print(f"[MOODLE SYNC] Terminé. {len(results)} fichiers traités.", flush=True)
    return results
