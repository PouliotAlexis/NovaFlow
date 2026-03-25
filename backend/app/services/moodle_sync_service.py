import sys
import asyncio

# Fix pour Windows : Nécessaire pour Playwright (sous-processus)
if sys.platform == "win32":
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import os
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from playwright.async_api import async_playwright, BrowserContext, Page
from app.core.config import settings
from .moodle_utils import normalize_moodle_url
from .document_dispatcher import dispatcher

logger = logging.getLogger("moodle_sync")
logging.basicConfig(level=logging.INFO)

class MoodleSyncService:
    def __init__(self):
        self.raw_url = settings.MOODLE_URL or "https://moodle.usherbrooke.ca"
        self.base_url = normalize_moodle_url(self.raw_url)
        self.user_data_dir = settings.CHROME_USER_DATA_DIR
        self.data_path = settings.MOODLE_DOWNLOADS_DESTINATION
        
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
            
        self._session_cache = {"valid": None, "timestamp": datetime.min}

    async def get_browser_context(self, playwright, headless: bool = True) -> BrowserContext:
        """Lance Playwright avec le profil Chrome de l'utilisateur."""
        try:
            logger.info(f"Lancement de Chrome avec le profil : {self.user_data_dir}")
            
            # Note: Si Chrome est déjà ouvert, ceci échouera sur Windows (Verrouillage de dossier)
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            logger.info("Navigateur lancé avec succès avec le profil utilisateur.")
            return context
        except Exception as e:
            error_str = str(e)
            if "Target page, context or browser has been closed" in error_str or "used by another process" in error_str:
                logger.error("OUPS ! Impossible de lancer Chrome car il est déjà OUVERT.")
                logger.error("CONSEIL : Ferme TOUTES tes fenêtres Chrome et réessaie pour utiliser ta session active.")
            else:
                logger.error(f"Erreur lors du lancement de Chrome avec profil: {e}")
            
            logger.info("Tentative de lancement sans profil (mode invité) - La session Moodle ne sera pas disponible.")
            return await playwright.chromium.launch(headless=headless)

    async def check_session_validity(self, page: Page) -> bool:
        """Vérifie si l'utilisateur est connecté à Moodle avec timeout."""
        try:
            url_to_check = f"{self.base_url}/my/"
            logger.info(f"Vérification de session sur : {url_to_check}")
            # Réduire le timeout pour éviter le "loading" infini
            await page.goto(url_to_check, wait_until="domcontentloaded", timeout=15000)
            logger.info(f"Page chargée : {page.url}")
            # Si on est sur une page de login ou que l'URL ne contient pas 'my', on n'est probablement pas connecté
            if "login" in page.url or "my" not in page.url:
                logger.info(f"Session Moodle non détectée (URL: {page.url})")
                return False
            
            # Si on est sur le dashboard, on considère que c'est valide par défaut
            if "/my/" in page.url:
                logger.info("Navigateur sur le dashboard. Session considérée valide.")
                return True

            # Vérification via sesskey (plus précis mais plus lent car nécessite JS execution)
            sesskey = await page.evaluate("window.M ? window.M.cfg.sesskey : null")
            if sesskey:
                logger.info("Session Moodle confirmée via sesskey.")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de session: {e}")
            return False

    async def check_session_validity_cached(self, playwright=None) -> bool:
        """Version cachée de la vérification de session avec loop dédiée pour Windows."""
        if playwright:
            # Si on a déjà un contexte playwright (déjà dans le thread dédié), on continue
            return await self._perform_check(playwright)
        
        return await asyncio.to_thread(self._run_check_in_thread)

    def _run_check_in_thread(self):
        new_loop = asyncio.new_event_loop()
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        async def _inner():
            async with async_playwright() as p:
                return await self._perform_check(p)
        
        try:
            return new_loop.run_until_complete(_inner())
        finally:
            new_loop.close()

    async def _perform_check(self, p):
        try:
            context = await self.get_browser_context(p, headless=True)
            page = await context.new_page()
            is_valid = await self.check_session_validity(page)
            await context.close()
            self._session_cache = {"valid": is_valid, "timestamp": datetime.now()}
            return is_valid
        except Exception as e:
            logger.error(f"Erreur _perform_check: {e}")
            return False

    async def login_interactively(self) -> dict:
        """Ouvre une fenêtre de navigateur (Threadé pour Windows). Retourne un dict {success, error}."""
        return await asyncio.to_thread(self._run_login_thread)

    def _run_login_thread(self) -> dict:
        new_loop = asyncio.new_event_loop()
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        async def _inner():
            async with async_playwright() as p:
                try:
                    context = await self.get_browser_context(p, headless=False)
                    page = await context.new_page()
                    await page.goto(f"{self.base_url}/login/index.php", wait_until="domcontentloaded")
                    
                    try:
                        await page.wait_for_url("**/my/**", timeout=300000)
                        is_valid = True
                        error = None
                    except Exception:
                        is_valid = False
                        error = "Délai d'attente dépassé ou connexion non complétée."
                    
                    await context.close()
                    self._session_cache = {"valid": is_valid, "timestamp": datetime.now()}
                    return {"success": is_valid, "error": error}
                except Exception as e:
                    msg = str(e)
                    if "Target page, context or browser has been closed" in msg:
                        msg = "Profil Chrome verrouillé. Ferme Chrome et réessaie."
                    logger.error(f"Erreur login_interactively: {e}")
                    return {"success": False, "error": msg}
        
        try:
            return new_loop.run_until_complete(_inner())
        finally:
            new_loop.close()

    async def run_sync(self):
        """Cycle principal de synchronisation (Threadé pour Windows)."""
        return await asyncio.to_thread(self._run_sync_thread)

    def _run_sync_thread(self):
        new_loop = asyncio.new_event_loop()
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        async def _inner():
            async with async_playwright() as p:
                try:
                    context = await self.get_browser_context(p)
                    page = await context.new_page()
                    
                    if not await self.check_session_validity(page):
                        logger.warning("Synchronisation avortée: session invalide.")
                        await context.close()
                        return {"status": "MOODLE_DISCONNECTED", "timestamp": datetime.now()}

                    # Phase 2: Découverte des cours
                    courses = await self.get_courses(page)
                    logger.info(f"{len(courses)} cours trouvés.")
                    
                    for course in courses:
                        logger.info(f"Scraping du cours: {course['name']}")
                        await self.scan_course_sections(page, course)
                    
                    await context.close()
                    return {"status": "SUCCESS", "courses_scanned": len(courses), "timestamp": datetime.now()}
                    
                except Exception as e:
                    import traceback
                    logger.error(f"Échec de la synchronisation: {traceback.format_exc()}")
                    return {"status": "ERROR", "message": str(e), "timestamp": datetime.now()}

        try:
            return new_loop.run_until_complete(_inner())
        finally:
            new_loop.close()

    async def get_courses(self, page: Page) -> List[dict]:
        """Récupère la liste des cours depuis la page 'My Courses'."""
        await page.goto(f"{self.base_url}/my/courses.php", wait_until="networkidle")
        
        # On cherche les cartes de cours ou les liens
        # Moodle v4 utilise souvent des sélecteurs comme .coursename
        courses = []
        course_elements = await page.query_selector_all("a.coursename")
        
        for el in course_elements:
            name = await el.inner_text()
            url = await el.get_attribute("href")
            # Extraire l'ID du cours de l'URL (?id=XXX)
            course_id = url.split("id=")[-1] if "id=" in url else None
            if course_id:
                courses.append({"id": course_id, "name": name.strip(), "url": url})
        
        return courses

    async def scan_course_sections(self, page: Page, course: dict):
        """Scanne les sections d'un cours spécifique avec une organisation granulaire."""
        await page.goto(course["url"], wait_until="networkidle")
        logger.info(f"Scanning sections pour {course['name']}...")
        
        # Moodle v4 affiche souvent les sections dans .course-content
        # On essaie plusieurs sélecteurs courants
        sections = await page.query_selector_all("li.section.main, div.section.main")
        if not sections:
            # Fallback pour d'autres thèmes Moodle
            sections = await page.query_selector_all(".content .section")

        for section in sections:
            section_name_el = await section.query_selector(".sectionname, h3.section-title")
            section_name = await section_name_el.inner_text() if section_name_el else "Général"
            section_name = section_name.strip().replace("/", "-").replace(":", "-") # Sanitization
            
            logger.info(f"  Section: {section_name}")

            # 1. Scraping des Ressources (Fichiers directs)
            # On cherche les fichiers (pdf, docx, etc.)
            resource_links = await section.query_selector_all("li.activity.resource a, div.activity.resource a")
            for res_link in resource_links:
                res_url = await res_link.get_attribute("href")
                if res_url and "mod/resource" in res_url:
                    await self.download_resource(page, res_link, course["name"], section_name, "Cours")

            # 2. Scraping des Devoirs (Assignments)
            # On entre dans chaque devoir pour voir s'il y a des documents joints
            assign_links = await section.query_selector_all("li.activity.assign a, div.activity.assign a")
            for assign_link in assign_links:
                assign_url = await assign_link.get_attribute("href")
                if assign_url and "mod/assign" in assign_url:
                    assign_name_el = await assign_link.query_selector(".instancename")
                    assign_name = await assign_name_el.inner_text() if assign_name_el else "Devoir"
                    assign_name = assign_name.replace("Devoir", "").strip() # Nettoyer "Devoir Devoir"
                    
                    logger.info(f"    Vérification devoir: {assign_name}")
                    # On ouvre le devoir dans un nouvel onglet ou la même page
                    await self.scan_assignment_files(page, assign_url, course["name"], section_name, assign_name)
                    # On revient en arrière pour continuer le scan de la section
                    await page.goto(course["url"], wait_until="domcontentloaded")

    async def scan_assignment_files(self, page: Page, url: str, course_name: str, section_name: str, assign_name: str):
        """Explore une page de devoir pour extraire les fichiers fournis par l'enseignant."""
        try:
            await page.goto(url, wait_until="networkidle")
            
            # Dans un devoir, les fichiers peuvent être dans :
            # - La description (.intro)
            # - La zone de fichiers joints (.submissionstatustable ou .fileupload)
            
            # On cherche tous les liens de fichiers typiques dans la zone de contenu
            file_links = await page.query_selector_all(".intro a, .submissionstatustable a, .fp-filename-icon a")
            
            download_count = 0
            for link in file_links:
                href = await link.get_attribute("href")
                if href and ("forcedownload=1" in href or "pluginfile.php" in href):
                    # On s'assure que c'est un fichier et pas un lien vers une autre page
                    await self.download_resource(page, link, course_name, section_name, f"Devoirs/{assign_name}")
                    download_count += 1
            
            if download_count > 0:
                logger.info(f"      {download_count} fichiers récupérés dans le devoir '{assign_name}'")
                
        except Exception as e:
            logger.warning(f"  Erreur lors du scan du devoir {url}: {e}")

    async def download_resource(self, page: Page, element, course_name: str, section_name: str, sub_type: str):
        """Gère le téléchargement, le renommage intelligent et l'organisation locale."""
        try:
            # On clique et on attend le téléchargement
            async with page.expect_download(timeout=30000) as download_info:
                await element.click()
            download = await download_info.value
            
            filename = download.suggested_filename
            # Organisation: data/moodle/Nom_Cours/Nom_Section/Type/Fichier
            target_dir = os.path.join(self.data_path, course_name, section_name, sub_type)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            file_path = os.path.join(target_dir, filename)
            
            # Éviter d'écraser si le fichier existe déjà (ou alors vérifier la date)
            if os.path.exists(file_path):
                logger.debug(f"Fichier déjà présent: {filename}")
                return

            await download.save_as(file_path)
            logger.info(f"Sauvegardé : {course_name} > {section_name} > {filename}")
            
            # Dispatcher pour indexation RAG
            try:
                text = dispatcher.extract_text(file_path)
                if text:
                    md_content = dispatcher.normalize_to_markdown(text, filename)
                    md_path = file_path + ".md"
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    logger.info(f"  Indexé RAG : {filename}.md")
            except Exception as e:
                logger.error(f"  Erreur extraction RAG pour {filename}: {e}")
                
        except Exception as e:
            # Certains clics ne déclenchent pas de téléchargement (liens externes)
            # On ignore silencieusement ou on log en debug
            logger.debug(f"Clic ressource n'a pas déclenché de download direct: {e}")

moodle_service = MoodleSyncService()

if __name__ == "__main__":
    # Test local
    asyncio.run(moodle_service.run_sync())
