import os
import httpx
import asyncio
from typing import List, Dict, Any
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
from app.services.rag_engine.ingest import ingest_document
from app.core.config import settings

async def capture_moodle_token(url: str):
    """
    Ouvre une fenêtre Chromium pour capturer le token SSO Moodle.
    Nécessite la connexion manuelle de l'utilisateur.
    """
    from playwright.async_api import async_playwright
    import json
    import time
    
    base_url = normalize_moodle_url(url)
    # On utilise l'URL de l'app mobile pour forcer la génération de token
    launch_url = f"{base_url}/admin/tool/mobile/launch.php?service=moodle_mobile_app&urlscheme=moodlemobile"
    
    token = None
    
    # On prépare l'URL de bypass pour l'utilisateur au cas où le serveur ne peut pas l'ouvrir
    bypass_url = launch_url
    
    async with async_playwright() as p:
        try:
            # On tente de lancer le navigateur
            # NOTE: headless=False ne fonctionnera PAS sur un serveur (Render/Vercel)
            # sans configuration de display virtuel (Xvfb).
            browser = await p.chromium.launch(headless=False, args=["--app=" + launch_url])
        except Exception as e:
            print(f"[MOODLE SSO] ❌ Impossible de lancer le navigateur : {e}")
            # Bypasser en proposant l'URL à l'utilisateur
            return {"error": "headless_incompatible", "bypass_url": bypass_url}
            
        page = await browser.new_page()
        
        print(f"[MOODLE SSO] En attente de connexion sur {base_url}...")
        
        # On surveille l'URL pour la redirection moodlemobile://token=xxx
        try:
            while not token:
                try:
                    current_url = page.url
                    if "token=" in current_url:
                        token = current_url.split("token=")[1].split("&")[0]
                        print(f"[MOODLE SSO] ✅ Token capturé !")
                        break
                    
                    if page.is_closed():
                        break
                except Exception:
                    break
                await asyncio.sleep(0.5)
        finally:
            await browser.close()
            
    return token


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
            raise KeyError(f"Erreur d'authentification Moodle : {data.get('error', 'Inconnue')}")

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
    ALLOWED_EXTENSIONS = (
        ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv",
        ".jpg", ".jpeg", ".png", ".gif", ".svg"
    )

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
        files_to_sync = []
        
        for section in contents:
            for module in section.get("modules", []):
                modname = module.get("modname")
                
                # 1. Ressources directes (File)
                if modname == "resource":
                    for content in module.get("contents", []):
                        if content.get("type") == "file":
                            files_to_sync.append({
                                "url": content.get("fileurl"),
                                "name": content.get("filename"),
                                "mtime": content.get("timemodified", 0),
                                "modname": modname
                            })
                
                # 2. Devoirs (Assign) - Fichiers joints à la consigne
                elif modname == "assign":
                    # Moodle stocke les pièces jointes d'intro dans introattachments
                    for attachment in module.get("introattachments", []):
                        files_to_sync.append({
                            "url": attachment.get("fileurl"),
                            "name": attachment.get("filename"),
                            "mtime": attachment.get("timemodified", 0),
                            "modname": modname
                        })
        
        # Filtrage et téléchargement
        synced_in_course = 0
        for f_info in files_to_sync:
            file_name = f_info["name"]
            
            # Vérifier l'extension
            if not file_name.lower().endswith(ALLOWED_EXTENSIONS):
                continue
                
            file_url = f_info["url"]
            remote_mtime = f_info["mtime"]
            file_path = os.path.abspath(os.path.join(course_dir, file_name))
            
            # Skip si déjà téléchargé ET pas mis à jour côté Moodle
            if os.path.exists(file_path):
                try:
                    local_mtime = int(os.path.getmtime(file_path))
                    if remote_mtime and local_mtime >= remote_mtime:
                        continue # Déjà à jour silencieusement
                except Exception:
                    pass
            
            # Téléchargement
            try:
                print(f"[MOODLE SYNC]   📥 Sync ({f_info['modname']}): {file_name}", flush=True)
                downloaded_path = await service.download_file(file_url, course_dir, file_name)
                synced_in_course += 1
                
                # Ingestion RAG (si supporté par ingest_document)
                try:
                    ingest_result = await asyncio.to_thread(ingest_document, downloaded_path, course_id=str(course_id))

                    results.append({
                        "course": course_name,
                        "file": file_name,
                        "status": "synced",
                        "rag": ingest_result
                    })
                except Exception as ir:
                    print(f"[MOODLE SYNC]   ⚠️ RAG Skip {file_name}: {ir}", flush=True)
                    results.append({
                        "course": course_name,
                        "file": file_name,
                        "status": "synced_no_rag"
                    })
            except Exception as e:
                print(f"[MOODLE SYNC]   ❌ ERREUR {file_name}: {e}", flush=True)
                results.append({
                    "course": course_name,
                    "file": file_name,
                    "status": "error",
                    "error": str(e)
                })
        
        if synced_in_course > 0:
            print(f"[MOODLE SYNC]   → {synced_in_course} nouveau(x) fichier(s) synchronisé(s)", flush=True)
    
    print(f"[MOODLE SYNC] Terminé. {len(results)} fichiers traités au total.", flush=True)
    return results

def normalize_moodle_url(url: str) -> str:
    """
    Extrait la base URL d'un lien Moodle (qu'il s'agisse de la racine, du login, 
    d'un cours ou d'un flux calendrier).
     Exemple: https://moodle.usherbrooke.ca/calendar/export_execute.php?userid=...
    Devient: https://moodle.usherbrooke.ca
    """
    from urllib.parse import urlparse, urlunparse
    if not url:
        return ""
    
    parsed = urlparse(url)
    # On ne garde que le scheme et le netloc (ex: https://moodle.usherbrooke.ca)
    base = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    return base.rstrip("/")
